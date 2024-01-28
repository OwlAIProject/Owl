import os
import asyncio
from datetime import datetime, timezone
from queue import Queue
import logging
from ..services.stt.streaming.streaming_transcription_service_factory import StreamingTranscriptionServiceFactory
from ..services.endpointing.streaming.streaming_endpointing_service import StreamingEndpointingService
from ..files import CaptureFile, CaptureSegmentFile
from ..files.wav_file import append_to_wav_file

logger = logging.getLogger(__name__)

class StreamingCaptureHandler:
    def __init__(self, app_state, device_name, capture_uuid, file_extension="aac", stream_format=None):
        self.app_state = app_state
        self.device_name = device_name
        self.capture_uuid = capture_uuid
        self.file_extension = file_extension
        self.segment_file = None
        self.transcription_service = StreamingTranscriptionServiceFactory.get_service(
            app_state.config, self.handle_utterance, stream_format=stream_format
        )
        
        self.endpointing_service = StreamingEndpointingService(
            timeout_interval=app_state.config.conversation_endpointing.timeout_interval,
            min_utterances=app_state.config.conversation_endpointing.min_utterances,
            endpoint_callback=lambda: asyncio.create_task(self.on_endpoint())
        )

        self._init_capture_session()

    def _init_capture_session(self):
        self.capture_file = CaptureFile(
            capture_directory=self.app_state.config.captures.capture_dir,
            capture_uuid=self.capture_uuid,
            device_type=self.device_name,
            timestamp=datetime.now(timezone.utc),
            file_extension=self.file_extension
        )
        self.start_new_segment()

    async def on_endpoint(self):
        logger.info(f"Endpoint detected for capture_uuid {self.capture_uuid}")
        if self.capture_file and self.segment_file:
            self._process_conversation(self.capture_file, self.segment_file)
        self.start_new_segment()

    def _process_conversation(self, capture_file: CaptureFile, segment_file: CaptureSegmentFile):
        logger.info(f"Processing conversation for capture_uuid={capture_file.capture_uuid} (conversation_uuid={segment_file.conversation_uuid})")

        task = (capture_file, segment_file)
        self.app_state.conversation_task_queue.put(task)

    async def handle_audio_data(self, binary_data):
        if self.file_extension == "wav":
            append_to_wav_file(
                filepath=self.capture_file.filepath, 
                sample_bytes=binary_data, 
                sample_rate=16000,
                sample_bits=16,
                num_channels=1
            )
            if self.segment_file:
                append_to_wav_file(
                    filepath=self.segment_file, 
                    sample_bytes=binary_data, 
                    sample_rate=16000, 
                    sample_bits=16, 
                    num_channels=1
                )
        else:
            with open(self.capture_file.filepath, "ab") as file:
                file.write(binary_data)

            if self.segment_file:
                with open(self.segment_file, "ab") as file:
                    file.write(binary_data)
        await self.transcription_service.send_audio(binary_data)

    async def handle_utterance(self, utterance):
        logger.info(f"Received utterance: {utterance}")
        asyncio.create_task(self.endpointing_service.utterance_detected())

    def start_new_segment(self):
        timestamp = datetime.now(timezone.utc)  # we are streaming in real-time, so we know start time
        self.segment_file = self.capture_file.create_conversation_segment(
            timestamp=timestamp,
            file_extension=self.file_extension
        )

    def finish_capture_session(self):
        if self.segment_file:
            self._process_conversation(capture_file=self.capture_file, segment_file=self.segment_file)
       
        capture_file = self.app_state.capture_sessions_by_id.pop(self.capture_uuid, None)
        if self.endpointing_service:
            self.endpointing_service.stop()
        logger.info(f"Finishing capture: {self.capture_uuid}")
        if capture_file:
            try:
                with open(capture_file.filepath, "a"):
                    pass  # Finalize the capture file
            except Exception as e:
                logger.error(f"Error closing file {capture_file.filepath}: {e}")