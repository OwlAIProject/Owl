from __future__ import annotations
import asyncio
from datetime import datetime, timezone
import logging
import uuid
from typing import TYPE_CHECKING

from ..services.stt.streaming.streaming_transcription_service_factory import StreamingTranscriptionServiceFactory
from ..services.endpointing.streaming.streaming_endpointing_service import StreamingEndpointingService
from ..files import CaptureFile, CaptureSegmentFile
from ..files.wav_file import append_to_wav_file
from ..models.schemas import UtteranceRead
from ..database.crud import create_utterance
from .task import Task
if TYPE_CHECKING:
    from .app_state import AppState

logger = logging.getLogger(__name__)

class ProcessConversationTask(Task):
    def __init__(self, capture_file: CaptureFile, segment_file: CaptureSegmentFile, conversation_uuid: str = None):
        self._capture_file = capture_file
        self._segment_file = segment_file
        self.conversation_uuid = conversation_uuid

    async def run(self, app_state: AppState):
        await app_state.conversation_service.process_conversation_from_audio(
            capture_file=self._capture_file,
            segment_file=self._segment_file,
            voice_sample_filepath=app_state.config.user.voice_sample_filepath,
            speaker_name=app_state.config.user.name,
            conversation_uuid=self.conversation_uuid
        )

Task.register(ProcessConversationTask)

class StreamingCaptureHandler:
    def __init__(self, app_state, device_name, capture_uuid, file_extension="aac"):
        self._app_state = app_state
        self._device_name = device_name
        self._capture_uuid = capture_uuid
        self._file_extension = file_extension
        self._segment_file = None
        self._conversation_uuid = None
        self._transcript_id = None
        self._capture_file = None
        self._transcript = None
        # infer from file extension
        self._stream_format = { "sample_rate": 16000, "encoding": "linear16" } if file_extension == "wav" else None
        self._transcription_service = StreamingTranscriptionServiceFactory.get_service(
            app_state.config, self.handle_utterance, stream_format=self._stream_format
        )
        
        self._endpointing_service = StreamingEndpointingService(
            timeout_seconds=app_state.config.conversation_endpointing.timeout_seconds,
            min_utterances=app_state.config.conversation_endpointing.min_utterances,
            endpoint_callback=lambda: asyncio.create_task(self.on_endpoint())
        )

    async def _init_capture_session(self):
        self._capture_file = CaptureFile(
            capture_directory=self._app_state.config.captures.capture_dir,
            capture_uuid=self._capture_uuid,
            device_type=self._device_name,
            timestamp=datetime.now(timezone.utc),
            file_extension=self._file_extension
        )

        await self._start_new_segment()

    async def on_endpoint(self):
        logger.info(f"Endpoint detected for capture_uuid {self._capture_uuid}")
        if self._capture_file and self._segment_file:
            self._process_conversation(self._conversation_uuid, self._capture_file, self._segment_file)
        await self._start_new_segment()

    def _process_conversation(self, conversation_uuid: str, capture_file: CaptureFile, segment_file: CaptureSegmentFile):
        logger.info(f"Processing conversation for capture_uuid={capture_file.capture_uuid} (conversation_uuid={segment_file.conversation_uuid})")
        task = ProcessConversationTask(conversation_uuid=conversation_uuid, capture_file=capture_file, segment_file=segment_file)
        self._app_state.task_queue.put(task)

    async def handle_audio_data(self, binary_data):
        if not self._capture_file:
            await self._init_capture_session()
        if self._file_extension == "wav":
            append_to_wav_file(
                filepath=self._capture_file.filepath, 
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
            with open(self._capture_file.filepath, "ab") as file:
                file.write(binary_data)

            if self._segment_file:
                with open(self._segment_file.filepath, "ab") as file:
                    file.write(binary_data)
        await self._transcription_service.send_audio(binary_data)

    async def handle_utterance(self, utterance):
        logger.info(f"Received utterance: {utterance}")
        asyncio.create_task(self._endpointing_service.utterance_detected())
        if self._transcript_id:
            utterance.transcription_id = self._transcript_id
        with next(self._app_state.database.get_db()) as db:
            create_utterance(db, utterance)
        await self._app_state.notification_service.emit_message("new_utterance",  {'conversation_uuid': self._conversation_uuid, 'utterance': UtteranceRead.from_orm(utterance).model_dump_json()})

    async def _start_new_segment(self):
        timestamp = datetime.now(timezone.utc)  # we are streaming in real-time, so we know start time
        self._segment_file = self._capture_file.create_conversation_segment(
            conversation_uuid=uuid.uuid1().hex,
            timestamp=timestamp,
            file_extension=self._file_extension
        )
        with next(self._app_state.database.get_db()) as db:
            saved_conversation = await self._app_state.conversation_service.create_conversation(self._capture_file, self._segment_file)
            self._conversation_uuid = saved_conversation.conversation_uuid
            self._transcript_id = saved_conversation.transcriptions[0].id

    def finish_capture_session(self):
        if self._segment_file:
            self._process_conversation(self._conversation_uuid, self._capture_file, self._segment_file)
       
        capture_file = self._app_state.capture_files_by_id.pop(self._capture_uuid, None)
        if self._endpointing_service:
            self._endpointing_service.stop()
        logger.info(f"Finishing capture: {self._capture_uuid}")
        if capture_file:
            try:
                with open(capture_file.filepath, "a"):
                    pass  # Finalize the capture file
            except Exception as e:
                logger.error(f"Error closing file {capture_file.filepath}: {e}")