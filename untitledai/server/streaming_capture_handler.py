from __future__ import annotations
from datetime import datetime, timezone
from io import BytesIO
import logging
from typing import TYPE_CHECKING

from pydub import AudioSegment

if TYPE_CHECKING:
    from .app_state import AppState
from .conversation_detection import submit_conversation_detection_task
from ..services.stt.streaming.streaming_transcription_service_factory import StreamingTranscriptionServiceFactory
from ..services import ConversationEndpointDetector
from ..files import CaptureFile
from ..files.wav_file import append_to_wav_file
from ..database.crud import create_utterance

logger = logging.getLogger(__name__)

class StreamingCaptureHandler:
    def __init__(self, app_state: AppState, device_name: str, capture_uuid: str, file_extension: str = "aac", stream_format=None):
        self._app_state = app_state
        self._device_name = device_name
        self._capture_uuid = capture_uuid
        self._file_extension = file_extension
        self._receive_buffer = bytes()
        self._min_buffer_size = 4096    # for PCM data, should be multiple of VAD window size (512)
        
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
        #TODO: this only works for PCM; need to implement AAC handling (i.e., wait for complete frames)
        self._receive_buffer += binary_data
        num_usable_bytes = len(self._receive_buffer) & ~1
        if num_usable_bytes < 4096:
            return
        sample_bytes = self._receive_buffer[0:num_usable_bytes]
        self._receive_buffer = self._receive_buffer[num_usable_bytes:]
                
        # Append to file on disk and create AudioSegment
        audio_chunk: AudioSegment = None
        if self._file_extension == "wav":
            append_to_wav_file(
                filepath=self._capture_file.filepath, 
                sample_bytes=sample_bytes, 
                sample_rate=16000,
                sample_bits=16,
                num_channels=1
            )
            audio_chunk = AudioSegment.from_file(
                file=BytesIO(sample_bytes),
                sample_width=2, # 16-bit (little endian implied)
                channels=1,
                frame_rate=16000,
                format="pcm"    # pcm/raw
            )
        else:
            with open(self._capture_file.filepath, "ab") as file:
                file.write(sample_bytes)
            audio_chunk = AudioSegment.from_file(
                file=BytesIO(sample_bytes),
                format="aac"
            )

        # Real-time transcription
        await self._transcription_service.send_audio(sample_bytes)

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