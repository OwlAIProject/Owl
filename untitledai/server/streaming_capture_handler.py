import os
import asyncio
from datetime import datetime, timezone
import logging
import uuid

from ..services.stt.streaming.streaming_transcription_service_factory import StreamingTranscriptionServiceFactory
from ..services.endpointing.streaming.streaming_endpointing_service import StreamingEndpointingService
from ..files import CaptureFile, CaptureSegmentFile
from ..files.wav_file import append_to_wav_file
from ..database.crud import create_utterance

logger = logging.getLogger(__name__)

class StreamingCaptureHandler:
    def __init__(self, app_state, device_name, capture_uuid, file_extension="aac", stream_format=None):
        self._app_state = app_state
        self._device_name = device_name
        self._capture_uuid = capture_uuid
        self._file_extension = file_extension
        self._segment_file = None
        self._transcription_service = StreamingTranscriptionServiceFactory.get_service(
            app_state.config, self._handle_utterance, stream_format=stream_format
        )
        
        self._endpointing_service = StreamingEndpointingService(
            timeout_interval=app_state.config.conversation_endpointing.timeout_interval,
            min_utterances=app_state.config.conversation_endpointing.min_utterances,
            endpoint_callback=lambda: asyncio.create_task(self.on_endpoint())
        )

        self._init_capture_session()

    def _init_capture_session(self):
        self.capture_file = CaptureFile(
            capture_directory=self._app_state.config.captures.capture_dir,
            capture_uuid=self._capture_uuid,
            device_type=self._device_name,
            timestamp=datetime.now(timezone.utc),
            file_extension=self._file_extension
        )
        self._start_new_segment()

    async def on_endpoint(self):
        logger.info(f"Endpoint detected for capture_uuid {self._capture_uuid}")
        if self.capture_file and self._segment_file:
            self._process_conversation(self.capture_file, self._segment_file)
        self._start_new_segment()

    def _process_conversation(self, capture_file: CaptureFile, segment_file: CaptureSegmentFile):
        logger.info(f"Processing conversation for capture_uuid={capture_file.capture_uuid} (conversation_uuid={segment_file.conversation_uuid})")

        task = (capture_file, segment_file)
        self._app_state.conversation_task_queue.put(task)

    async def handle_audio_data(self, binary_data):
        if self._file_extension == "wav":
            append_to_wav_file(
                filepath=self.capture_file.filepath, 
                sample_bytes=binary_data, 
                sample_rate=16000,
                sample_bits=16,
                num_channels=1
            )
            if self._segment_file:
                append_to_wav_file(
                    filepath=self._segment_file.filepath, 
                    sample_bytes=binary_data, 
                    sample_rate=16000, 
                    sample_bits=16, 
                    num_channels=1
                )
        else:
            with open(self.capture_file.filepath, "ab") as file:
                file.write(binary_data)

            if self._segment_file:
                with open(self._segment_file.filepath, "ab") as file:
                    file.write(binary_data)
        await self._transcription_service.send_audio(binary_data)

    async def _handle_utterance(self, utterance):
        logger.info(f"Received utterance: {utterance}")
        asyncio.create_task(self._endpointing_service.utterance_detected())
        with next(self._app_state.database.get_db()) as db:
            create_utterance(db, utterance)

    def _start_new_segment(self):
        timestamp = datetime.now(timezone.utc)  # we are streaming in real-time, so we know start time
        self._segment_file = self.capture_file.create_conversation_segment(
            conversation_uuid=uuid.uuid1().hex,
            timestamp=timestamp,
            file_extension=self._file_extension
        )

    def finish_capture_session(self):
        if self._segment_file:
            self._process_conversation(capture_file=self.capture_file, segment_file=self._segment_file)
       
        capture_file = self._app_state.capture_sessions_by_id.pop(self._capture_uuid, None)
        if self._endpointing_service:
            self._endpointing_service.stop()
        logger.info(f"Finishing capture: {self._capture_uuid}")
        if capture_file:
            try:
                with open(capture_file.filepath, "a"):
                    pass  # Finalize the capture file
            except Exception as e:
                logger.error(f"Error closing file {capture_file.filepath}: {e}")