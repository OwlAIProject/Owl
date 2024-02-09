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
import os
from multiprocessing import Queue, Process
from typing import List

from pydub import AudioSegment

from ...vad.time_segment import TimeSegment
from .conversation_endpoint_detector import ConversationEndpointDetector
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
class DetectConversations:
    capture_finished: bool
    audio_data: bytes | None
    format: str

@dataclass
class ExtractToFiles:
    conversations: List[TimeSegment]
    conversation_filepaths: List[str]

@dataclass
class TerminateProcess:
    pass

@dataclass
class DetectedConversationsResponse:
    conversations: List[TimeSegment]
    current_conversation_start_offset_milliseconds: int | None

@dataclass
class ExtractToFilesFinished:
    pass


####################################################################################################
# Service
####################################################################################################

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

        # Timestamps
        self._start_time = capture_timestamp
        self._current_conversation_start_time = None

        # Start process
        process_args = (
            self._request_queue.underlying_queue(),
            self._response_queue.underlying_queue(),
            config,
            capture_filepath
        )
        self._process = Process(target=ConversationDetectionService._run, args=process_args)
        self._process.start()

    def __del__(self):
        self._request_queue.underlying_queue().put(TerminateProcess())
        self._process.join()

    async def detect_conversations(self, audio_data: bytes | None, format: str, capture_finished: bool) -> List[TimeSegment]:
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
        List[TimeSegment]
            Zero or more conversations with timestamps in milliseconds.
        """
        assert format == "wav" or format == "aac"
        await self._request_queue.put(DetectConversations(capture_finished=capture_finished, audio_data=audio_data, format=format))
        response = await self._response_queue.get()
        if isinstance(response, DetectedConversationsResponse):
            self._current_conversation_start_time = None
            if response.current_conversation_start_offset_milliseconds is not None:
                self._current_conversation_start_time = self._start_time + timedelta(milliseconds=response.current_conversation_start_offset_milliseconds)
            return response.conversations
        return []
    
    async def current_conversation_start_time(self) -> datetime | None:
        """
        Returns
        -------
        datetime | None
            If a conversation is currently in progress, its start timem is returned. Otherwise, None
            if no conversation is currently in progress.
        """
        return self._current_conversation_start_time
    
    async def extract_conversations(self, conversations: List[TimeSegment], conversation_filepaths: List[str]):
        """
        Extracts conversations from the capture file (which is assumed to have been kept up-to-date)
        and writes them to conversation segment files.

        Parameters
        ----------
        conversations : List[TimeSegment]
            Conversation list within capture.
        
        conversation_filepaths : List[str]
            List of filepaths to write conversations to. Must correspond 1:1 with `conversations`.
        """
        assert len(conversations) == len(conversation_filepaths)
        await self._request_queue.put(ExtractToFiles(conversations=conversations, conversation_filepaths=conversation_filepaths))
        await self._response_queue.get()    # ExtractToFilesFinished

    def _run(request_queue: Queue, response_queue: Queue, config: Configuration, capture_filepath: str):
        detector = ConversationEndpointDetector(config=config, sampling_rate=16000)

        # Run process until termination signal
        while True:
            request = request_queue.get()
            
            # Command: terminate process
            if isinstance(request, TerminateProcess):
                break

            # Command: detect conversations and return to calling process
            elif isinstance(request, DetectConversations):
                request: DetectConversations = request

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
                        response_queue.put(DetectedConversationsResponse(conversations=[]))
                
                # Detect conversations and return them
                convos = detector.consume_samples(samples=audio_chunk, end_stream=request.capture_finished)
                response = DetectedConversationsResponse(
                    conversations=convos,
                    current_conversation_start_offset_milliseconds=detector.current_conversation_start_offset_milliseconds()
                )
                response_queue.put(response)

            # Command: extract conversations from capture file into their own files
            elif isinstance(request, ExtractToFiles):
                # Extract all conversations from capture file into their own files. As capture file
                # grows longer, this takes ever longer because we need to re-load the entire capture
                # file from start to finish.
                request: ExtractToFiles = request
                if len(request.conversations) > 0:
                    # Load entire capture
                    file_extension = os.path.splitext(capture_filepath)[1].lstrip(".")
                    audio = AudioSegment.from_file(file=capture_filepath, format=file_extension)
                    logger.info(f"Loaded: {capture_filepath}")

                    # Extract conversations into their own files
                    for i in range(len(request.conversations)):
                        convo = request.conversations[i]
                        conversation_audio = audio[convo.start:convo.end]
                        logger.info(f"Extracted: {convo}")
                        
                        # Export. Annoyingly, "aac" is not a valid ffmpeg output format and we need
                        # to use "adts".
                        #TODO: need a unified audio exporting function that handles this automatically
                        format = "adts" if file_extension == "aac" else file_extension
                        conversation_audio.export(out_f=request.conversation_filepaths[i], format=format)
                response_queue.put(ExtractToFilesFinished())