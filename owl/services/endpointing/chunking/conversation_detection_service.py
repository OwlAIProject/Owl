#
# conversation_detection_service.py
#
# Detects and extracts conversations from arbitrary chunks (i.e., non-streaming case). Operates in a
# subprocess to avoid blocking the server event loop and exposes an async interface. Responsible for
# accumulating raw audio data, audio conversion, conversation endpoint detection, and conversation
# extraction.
#

from dataclasses import dataclass
from datetime import datetime, timedelta
from io import BytesIO
import logging
from math import floor
import os
from multiprocessing import Queue, Process
from typing import List

from pydub import AudioSegment

from .conversation_endpoint_detector import ConversationEndpointDetector, DetectedConversation
from ....core.config import Configuration
from ....core.utils import AsyncMultiprocessingQueue


logger = logging.getLogger(__name__)


####################################################################################################
# Inter-process Communication
#
# Internal objects passed back and forth between the process and server. The async interface works
# by wrapping the multiprocessing.Queue with an async queue and sending/receiving these.
####################################################################################################

@dataclass
class DetectConversationsCommand:
    capture_finished: bool
    audio_data: bytes | None
    format: str

@dataclass
class ExtractToFilesCommand:
    conversations: List[DetectedConversation]
    conversation_filepaths: List[str]

@dataclass
class TerminateProcessCommand:
    pass

@dataclass
class DetectedConversationsCompletion:
    completed: List[DetectedConversation]
    in_progress: DetectedConversation | None

@dataclass
class ExtractToFilesCompletion:
    pass


####################################################################################################
# Service
####################################################################################################

@dataclass
class ConversationDetectionResult:
    """
    Conversations that were completed during the last call.
    """
    completed: List[DetectedConversation]

    """
    If there is a conversation in progress but not yet completed, its current state is returned
    here, otherwise None. The end time will be continuously updated to reflect the current audio
    offset from the start of the capture.
    """
    in_progress: DetectedConversation | None

class ConversationDetectionService:
    """
    Provides asynchronous methods for detecting conversations in an in-progress capture and
    extracting them to files. May only handle one capture session.
    """

    def __init__(self, config: Configuration, capture_filepath: str, capture_timestamp: datetime):
        """
        Instantiates the service for a particular capture file and starts a subprocess.

        Parameters
        ----------
        config : Configuration
            Configuration object.
        
        capture_filepath : str
            The capture file for the capture session this instance will handle. This is expected to
            be updated separately and before detection is invoked on each audio chunk.

        capture_timestamp : datetime
            Timestamp of the start of the capture.
        """
        self._request_queue = AsyncMultiprocessingQueue(queue=Queue())
        self._response_queue = AsyncMultiprocessingQueue(queue=Queue())

        # Conversation in progress
        self._conversation_in_progress = None

        # Start process
        process_args = (
            self._request_queue.underlying_queue(),
            self._response_queue.underlying_queue(),
            config,
            capture_filepath,
            capture_timestamp
        )
        self._process = Process(target=ConversationDetectionService._run, args=process_args)
        self._process.start()

    def __del__(self):
        self._request_queue.underlying_queue().put(TerminateProcessCommand())
        self._process.join()

    async def detect_conversations(self, audio_data: bytes | None, format: str, capture_finished: bool) -> ConversationDetectionResult:
        """
        Consumes audio data, one chunk at a time, and looks for conversations.

        Parameters
        ----------
        audio_data : bytes | None
            Audio data in bytes. Must be in complete frames (i.e., even number of bytes for 16-bit
            PCM data, complete AAC frames for AAC-encoded streams, etc.) so that it can be decoded
            and fed into the conversation detector.
        
        format : str
            Audio format: "wav" or "aac" only for now.
        
        capture_finished : bool
            Whether capture is finished. No calls should be made after this and `audio_data` may be
            None. This finalizes detection and yields any remaining conversation segment.
        
        Returns
        -------
        ConversationDetectionResult
            Zero or more finished conversations with timestamps in milliseconds and zero or one 
            conversations in progress with start timestamp and current (but not final) end time-
            stamp.
        """
        assert format == "wav" or format == "aac"
        await self._request_queue.put(DetectConversationsCommand(capture_finished=capture_finished, audio_data=audio_data, format=format))
        response = await self._response_queue.get()
        if isinstance(response, DetectedConversationsCompletion):
            # If there is a conversation in progress, hang on to it so it can be checked easily
            if capture_finished:
                self._conversation_in_progress = None
            else:
                self._conversation_in_progress = response.in_progress

            # Return detection results (completed *and* in-progress, if any)
            results = ConversationDetectionResult(
                completed=response.completed,
                in_progress=response.in_progress
            )
            return results
        return ConversationDetectionResult(completed=[], in_progress=None)
    
    def current_conversation_in_progress(self) -> DetectedConversation | None:
        """
        Returns
        -------
        DetectedConversation | None
            If a conversation is currently in progress, return it with timestamps so far. Otherwise,
            None if no conversation is currently in progress.
        """
        return self._conversation_in_progress
    
    async def extract_conversations(self, conversations: List[DetectedConversation], conversation_filepaths: List[str]):
        """
        Extracts conversations from the capture file (which is assumed to have been kept up-to-date)
        and writes them to conversation segment files.

        Parameters
        ----------
        conversations : List[DetectedConversation]
            Conversation list within capture.
        
        conversation_filepaths : List[str]
            List of filepaths to write conversations to. Must correspond 1:1 with `conversations`.
        """
        assert len(conversations) == len(conversation_filepaths)
        await self._request_queue.put(ExtractToFilesCommand(conversations=conversations, conversation_filepaths=conversation_filepaths))
        await self._response_queue.get()    # ExtractToFilesCompletion

    def _run(request_queue: Queue, response_queue: Queue, config: Configuration, capture_filepath: str, capture_timestamp: datetime):
        detector = ConversationEndpointDetector(config=config, start_time=capture_timestamp, sampling_rate=16000)

        # Run process until termination signal
        while True:
            request = request_queue.get()
            
            # Command: terminate process
            if isinstance(request, TerminateProcessCommand):
                break

            # Command: detect conversations and return to calling process
            elif isinstance(request, DetectConversationsCommand):
                request: DetectConversationsCommand = request

                # Convert audio
                audio_chunk: AudioSegment = None
                if request.audio_data and len(request.audio_data) > 0:
                    if request.format == "wav":
                        audio_chunk = AudioSegment.from_file(
                            file=BytesIO(request.audio_data),
                            sample_width=2, # 16-bit (little endian implied)
                            channels=1,
                            frame_rate=16000,
                            format="pcm"    # pcm/raw
                        )
                    elif request.format == "aac":
                        audio_chunk = AudioSegment.from_file(
                            file=BytesIO(request.audio_data),
                            format="aac"
                        )
                    else:
                        response_queue.put(DetectedConversationsCompletion(completed=[], in_progress=None))
                
                # Detect conversations and return them
                convos = detector.consume_samples(samples=audio_chunk, end_stream=request.capture_finished)
                response = DetectedConversationsCompletion(
                    completed=convos,
                    in_progress=detector.current_conversation_in_progress()
                )
                response_queue.put(response)

            # Command: extract conversations from capture file into their own files
            elif isinstance(request, ExtractToFilesCommand):
                # Extract all conversations from capture file into their own files. As capture file
                # grows longer, this takes ever longer because we need to re-load the entire capture
                # file from start to finish.
                request: ExtractToFilesCommand = request
                if len(request.conversations) > 0:
                    # Load entire capture
                    file_extension = os.path.splitext(capture_filepath)[1].lstrip(".")
                    audio = AudioSegment.from_file(file=capture_filepath, format=file_extension)
                    logger.info(f"Loaded: {capture_filepath}")

                    # Extract conversations into their own files
                    for i in range(len(request.conversations)):
                        # Get millisecond offsets from start of capture
                        convo = request.conversations[i]
                        start_millis = int(floor((convo.endpoints.start - capture_timestamp).total_seconds() * 1000 + 0.5))
                        end_millis = int(floor((convo.endpoints.end - capture_timestamp).total_seconds() * 1000 + 0.5))

                        # Slice out from the capture
                        conversation_audio = audio[start_millis:end_millis]
                        logger.info(f"Extracted: {convo}")
                        
                        # Export. Annoyingly, "aac" is not a valid ffmpeg output format and we need
                        # to use "adts".
                        #TODO: need a unified audio exporting function that handles this automatically
                        format = "adts" if file_extension == "aac" else file_extension
                        conversation_audio.export(out_f=request.conversation_filepaths[i], format=format)
                response_queue.put(ExtractToFilesCompletion())