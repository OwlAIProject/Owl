#TODO: remove streaming endpointing service and min_utterances from config
#TODO: tasks can be unified -- no need to re-enqueue
#TODO: detect ffmpeg sub-process errors and kill socket/finalize conversation?

from __future__ import annotations
from datetime import datetime, timezone
from io import BytesIO
import logging
import subprocess
from typing import Tuple, TYPE_CHECKING

from pydub import AudioSegment

if TYPE_CHECKING:
    from .app_state import AppState
from .conversation_detection import submit_conversation_detection_task
from ..services.stt.streaming.streaming_transcription_service_factory import StreamingTranscriptionServiceFactory
from ..services import ConversationEndpointDetector
from ..files import CaptureFile
from ..files.wav_file import append_to_wav_file
from ..database.crud import create_utterance
from ..core.utils.hexdump import hexdump
from ..files import AACFrameSequencer

logger = logging.getLogger(__name__)

class StreamingCaptureHandler:
    def __init__(self, app_state: AppState, device_name: str, capture_uuid: str, file_extension: str = "aac", stream_format=None):
        self._app_state = app_state
        self._device_name = device_name
        self._capture_uuid = capture_uuid
        self._file_extension = file_extension
        self._receive_buffer = bytes()
        self._aac_frame_sequencer = AACFrameSequencer()
        
        self._transcription_service = StreamingTranscriptionServiceFactory.get_service(
            app_state.config, self._handle_utterance, stream_format=stream_format
        )
        
        self._conversation_endpoint_detector = ConversationEndpointDetector(
            config=app_state.config,
            sampling_rate=16000
        )

        self._capture_file = CaptureFile(
            capture_directory=self._app_state.config.captures.capture_dir,
            capture_uuid=self._capture_uuid,
            device_type=self._device_name,
            timestamp=datetime.now(timezone.utc),
            file_extension=self._file_extension
        )

    async def handle_audio_data(self, binary_data):
        # Append to receive buffer until we have minimum required number of bytes, then take an even
        # number of bytes to ensure a whole number of 16-bit samples when format is raw PCM
        self._receive_buffer += binary_data
        num_usable_bytes = len(self._receive_buffer) & ~1
        if num_usable_bytes < 4096: # for PCM data, should be multiple of VAD window size (512)
            return
        received_bytes = self._receive_buffer[0:num_usable_bytes]
        self._receive_buffer = self._receive_buffer[num_usable_bytes:]
                
        # Append to file on disk and create AudioSegment
        audio_chunk: AudioSegment = None
        if self._file_extension == "wav":
            append_to_wav_file(
                filepath=self._capture_file.filepath, 
                sample_bytes=received_bytes, 
                sample_rate=16000,
                sample_bits=16,
                num_channels=1
            )
            audio_chunk = AudioSegment.from_file(
                file=BytesIO(received_bytes),
                sample_width=2, # 16-bit (little endian implied)
                channels=1,
                frame_rate=16000,
                format="pcm"    # pcm/raw
            )
        elif self._file_extension == "aac":
            # Write to disk directly
            with open(self._capture_file.filepath, "ab") as file:
                file.write(received_bytes)

            # Extract complete AAC frames
            complete_frames = self._aac_frame_sequencer.get_next_frames(received_bytes=received_bytes)
            if len(complete_frames) == 0:
                return
            
            # Create an audio object
            try:
                audio_chunk = AudioSegment.from_file(
                    file=BytesIO(complete_frames),
                    format="aac"
                )
            except Exception:
                #hexdump(complete_frames)
                # with open("broken.aac", "wb") as fp:
                #     fp.write(complete_frames)
                return
        else:
            raise ValueError(f"Unsupported audio format: {self._file_extension}")

        # Real-time transcription
        await self._transcription_service.send_audio(received_bytes)

        # Conversation detection
        submit_conversation_detection_task(
            task_queue=self._app_state.conversation_detection_task_queue,
            capture_file=self._capture_file,
            detector=self._conversation_endpoint_detector,
            capture_uuid=self._capture_file.capture_uuid,
            samples=audio_chunk
        )

    async def _handle_utterance(self, utterance):
        #logger.info(f"Received utterance: {utterance}")
        pass

    def finish_capture_session(self):
        # Finalize conversation detection
        submit_conversation_detection_task(
            task_queue=self._app_state.conversation_detection_task_queue,
            capture_file=self._capture_file,
            detector=self._conversation_endpoint_detector,
            capture_uuid=self._capture_file.capture_uuid,
            samples=None,
            capture_finished=True
        )
        logger.info(f"Finishing capture: {self._capture_uuid}")