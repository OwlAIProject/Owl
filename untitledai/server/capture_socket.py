#
# capture_socket.py
#
# Socket handlers for streaming audio capture.
#
# Using namespace objects to implement socketio event handlers: 
# https://python-socketio.readthedocs.io/en/latest/server.html#class-based-namespaces
#
import os
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi import FastAPI
import socketio
import json
import time
from ..services.conversation.conversation_service import ConversationService
from ..services.stt.streaming.streaming_transcription_service_factory import StreamingTranscriptionServiceFactory
from ..models.schemas import ConversationRead, Conversation

class CaptureSocketApp(socketio.AsyncNamespace):
    def __init__(self, app_state):
        super(CaptureSocketApp, self).__init__(namespace="*")

        self._app_state = app_state
        self.transcription_service = StreamingTranscriptionServiceFactory.get_service(
            app_state.config, self._handle_utterance
        )
        self.audio_directory = self._app_state._get_audio_directory()
        self._current_conversation_id = None
        self._current_file = None
        self._current_file_name = ""
        self._last_utterance_time = None
        self._conversation_timeout_threshold = 10

        self._sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
        self._app = socketio.ASGIApp(self._sio)
        self._sio.register_namespace(self)

        self._timer_task = None

    async def start_timer(self):
        if not self._timer_task:
            self._timer_task = asyncio.create_task(self._check_conversation_timeout())

    def mount_to(self, app: FastAPI, at_path: str):
        app.mount(path=at_path, app=self._app)

    async def _handle_utterance(self, utterance):
        print(f"Received utterance: {utterance}")
        self._last_utterance_time = datetime.now()

    async def on_connect(self, path, sid, *args):
        print('Connected: ', sid)
        await self.start_timer()

    async def on_disconnect(self, path, sid, *args):
        print('Disconnected: ', sid)

    async def on_audio_data(self, path, sid, binary_data, device_name):
        if not self._current_conversation_id:
            timestamp = time.strftime("%Y%m%d%H%M%S")
            sanitized_device_name = "".join(char for char in device_name if char.isalnum())
            self._current_file_name = os.path.join(self.audio_directory, f"{timestamp}_{sanitized_device_name}.aac")
            self._current_file = open(self._current_file_name, "ab")
            self._current_conversation_id = uuid4().hex

        if self._current_file is not None:
            try:
                self._current_file.write(binary_data)
            except Exception as e:
                print(f"Error writing to file: {e}")
        else:
            print("Error: Current file is not open.")

        await self.transcription_service.send_audio(binary_data)

    async def on_finish_audio(self, path, sid):
        if self._current_conversation_id:
            await self._close_and_process_current_file()
            self._current_conversation_id = None

    async def _close_and_process_current_file(self):
        if self._current_file:
            self._current_file.close()
            self._current_file = None
            print(f"File {self._current_file_name} closed.")

            try:
                processing_task = asyncio.create_task(
                    self._app_state.conversation_service.process_conversation_from_audio(self._current_file_name)
                )

                saved_transcription, saved_conversation = await processing_task
                with next(self._app_state.database.get_db()) as db:
                    saved_conversation = db.query(Conversation).get(saved_conversation.id)
                    db.refresh(saved_conversation)
                    conversation_data = ConversationRead.from_orm(saved_conversation).dict()
                    conversation_json = json.dumps(conversation_data)
                    await self._sio.emit('new_conversation', conversation_json)
            except Exception as e:
                print(f"Error processing session from audio: {e}")

            self._current_file_name = ""
            self._last_utterance_time = None
    async def _check_conversation_timeout(self):
        while True:
            await asyncio.sleep(1)
            if self._current_conversation_id and self._last_utterance_time:
                if (datetime.now() - self._last_utterance_time) > timedelta(seconds=self._conversation_timeout_threshold):
                    self._current_conversation_id = None
                    await self._close_and_process_current_file()
