#
# capture_socket.py
#
# Socket handlers for streaming audio capture.
#
# Using namespace objects to implement socketio event handlers: 
# https://python-socketio.readthedocs.io/en/latest/server.html#class-based-namespaces
#
import asyncio
import os
import logging
from datetime import datetime, timedelta
from fastapi import FastAPI
from queue import Queue
import socketio
from uuid import uuid4
import time
from datetime import timezone
import json
from ..services.conversation.conversation_service import ConversationService
from ..services.stt.streaming.streaming_transcription_service_factory import StreamingTranscriptionServiceFactory
from ..models.schemas import ConversationRead, Conversation
from ..files import CaptureFile

logger = logging.getLogger(__name__)

class CaptureHandler:
    def __init__(self, app_state, conversation_timeout_threshold=30):
        self._app_state = app_state
        self._conversation_timeout_threshold = conversation_timeout_threshold
        self._last_utterance_time = None
        self._conversations_queue = Queue()

    def notify_utterance_received(self):
        self._last_utterance_time = datetime.now()

    def handle_capture(self, binary_data, device_name, capture_id):
        capture_file = self._app_state.capture_sessions_by_id.get(capture_id)
        if not capture_file:
            capture_file = CaptureFile(
                audio_directory=self._app_state.get_audio_directory(),
                capture_id=capture_id,
                device_type=device_name,
                timestamp=datetime.now(timezone.utc),
                file_extension="aac"
            )
            self._app_state.capture_sessions_by_id[capture_id] = capture_file
            logger.info(f"New capture started: {capture_file.capture_id} ({capture_file.filepath})")

        with open(capture_file.filepath, "ab") as file:
            file.write(binary_data)

    def finish_conversation(self, capture_id):
        capture_file = self._app_state.capture_sessions_by_id.pop(capture_id, None)
        if capture_file:
            try:
                with open(capture_file.filepath, "a"): 
                    pass
            except Exception as e:
                logger.error(f"Error closing file {capture_file.filepath}: {e}")
            self._conversations_queue.put(capture_file)
            logger.info(f"Finished conversation: {capture_file.capture_id}")
        else:
            logger.error(f"Error: No capture file found for {capture_id}")
        self._last_utterance_time = None

    def check_conversation_timeout(self):
        pass
        # if self._current_capture_file and self._last_utterance_time:
        #     if (datetime.now() - self._last_utterance_time) > timedelta(seconds=self._conversation_timeout_threshold):
        #         self.finish_conversation()

class CaptureSocketApp(socketio.AsyncNamespace):
    def __init__(self, app_state):
        super().__init__(namespace="*")
        self._app_state = app_state
        self.transcription_service = StreamingTranscriptionServiceFactory.get_service(app_state.config, self.handle_utterance)
        self.capture_handler = CaptureHandler(app_state)
        self._sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
        self._app = socketio.ASGIApp(self._sio)
        self._sio.register_namespace(self)
        self._processing_task = None

    def mount_to(self, app: FastAPI, at_path: str):
        app.mount(path=at_path, app=self._app)

    async def handle_utterance(self, utterance):
        self.capture_handler.notify_utterance_received()
        logger.info(f"Received utterance: {utterance}")

    async def on_connect(self, path, sid, *args):
        logger.info(f'Connected: {sid}')
        self.start()

    async def on_disconnect(self, path, sid, *args):
        logger.info(f'Disconnected: {sid}')

    async def on_audio_data(self, path, sid, binary_data, device_name, capture_id, *args):
        self.capture_handler.handle_capture(binary_data, device_name, capture_id)
        await self.transcription_service.send_audio(binary_data)

    async def on_finish_audio(self, path, sid, capture_id, *args):
        logger.info(f"Client signalled end of audio stream for {capture_id}")
        self.capture_handler.finish_conversation(capture_id)
        
    async def process_conversations(self):
        if not self.capture_handler._conversations_queue.empty():
                capture_file: CaptureFile = self.capture_handler._conversations_queue.get()
                logger.info(f"Processing conversation: {capture_file.capture_id}")
                try:
                    processing_task = asyncio.create_task(
                        self._app_state.conversation_service.process_conversation_from_audio(capture_file=capture_file)
                    )
                    saved_transcription, saved_conversation = await processing_task
                    with next(self._app_state.database.get_db()) as db:
                        saved_conversation = db.query(Conversation).get(saved_conversation.id)
                        db.refresh(saved_conversation)
                        conversation_data = ConversationRead.from_orm(saved_conversation)
                        conversation_json = conversation_data.json()

                        await self._sio.emit('new_conversation', conversation_json)
                except Exception as e:
                    logger.error(f"Error processing session from audio: {e}")

    async def _timer(self):
        while True:
            self.capture_handler.check_conversation_timeout()
            await self.process_conversations()
            await asyncio.sleep(1) 

    def start(self):
        if not self._processing_task:
            self._processing_task = asyncio.create_task(self._timer())
        return self._processing_task