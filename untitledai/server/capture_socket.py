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
import json
from ..services.conversation.conversation_service import ConversationService
from ..services.stt.streaming.streaming_transcription_service_factory import StreamingTranscriptionServiceFactory
from ..models.schemas import ConversationRead, Conversation

logger = logging.getLogger(__name__)

class CaptureHandler:
    def __init__(self, app_state, conversation_timeout_threshold=30):
        self._app_state = app_state
        self._conversation_timeout_threshold = conversation_timeout_threshold
        self._conversations_queue = Queue()
        self._current_capture_id = None
        self._current_file = None
        self._current_file_name = ""
        self._last_utterance_time = None

    def notify_utterance_received(self):
        self._last_utterance_time = datetime.now()

    def handle_capture(self, binary_data, device_name):
        if not self._current_capture_id:
            timestamp = time.strftime("%Y%m%d%H%M%S")
            sanitized_device_name = "".join(char for char in device_name if char.isalnum())
            self._current_file_name = os.path.join(self._app_state.get_audio_directory(), f"{timestamp}_{sanitized_device_name}.aac")
            self._current_file = open(self._current_file_name, "ab")
            self._current_capture_id = uuid4().hex
            logger.info(f"New capture started: {self._current_capture_id} ({self._current_file_name})")

        if self._current_file is not None:
            try:
                self._current_file.write(binary_data)
            except Exception as e:
                logger.error(f"Error writing to file: {e}")
        else:
            logger.error("Error: Current file is not open.")

    def finish_conversation(self):
        if self._current_file:
            self._current_file.close()
            self._conversations_queue.put((self._current_file_name, self._current_capture_id))
            self._current_file = None
            self._current_capture_id = None
            self._current_file_name = ""
            self._last_utterance_time = None

    def check_conversation_timeout(self):
        if self._current_capture_id and self._last_utterance_time:
            if (datetime.now() - self._last_utterance_time) > timedelta(seconds=self._conversation_timeout_threshold):
                self.finish_conversation()

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

    async def on_audio_data(self, path, sid, binary_data, device_name, *args):
        self.capture_handler.handle_capture(binary_data, device_name)
        await self.transcription_service.send_audio(binary_data)

    async def on_finish_audio(self, path, sid, *args):
        logger.info(f"Client signalled end of audio stream")
        self.capture_handler.finish_conversation()
        
    async def process_conversations(self):
        if not self.capture_handler._conversations_queue.empty():
                fn, cid = self.capture_handler._conversations_queue.get()
                logger.info(f"Processing conversation: {cid}")
                try:
                    processing_task = asyncio.create_task(
                        self._app_state.conversation_service.process_conversation_from_audio(fn)
                    )
                    saved_transcription, saved_conversation = await processing_task
                    with next(self._app_state.database.get_db()) as db:
                        saved_conversation = db.query(Conversation).get(saved_conversation.id)
                        db.refresh(saved_conversation)
                        conversation_data = ConversationRead.from_orm(saved_conversation).dict()
                        conversation_json = json.dumps(conversation_data)
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