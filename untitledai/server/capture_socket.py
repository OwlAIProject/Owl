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
from ..services.conversation.conversation_service import ConversationService
from ..services.stt.streaming.streaming_transcription_service_factory import StreamingTranscriptionServiceFactory


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

    def mount_to(self, app: FastAPI, at_path: str):
        app.mount(path=at_path, app=self._app)

    async def _handle_utterance(self, utterance):
        print(f"Received utterance: {utterance}")
        self._last_utterance_time = datetime.now()

    async def on_connect(self, path, sid, *args):
        print('Connected: ', sid)

    async def on_disconnect(self, path, sid, *args):
        print('Disconnected: ', sid)

    async def on_audio_data(self, path, sid, binary_data):
        if not self._current_conversation_id:
            self._current_conversation_id = uuid4().hex
            self._current_file_name = os.path.join(self.audio_directory, f"audio_{self._current_conversation_id}.aac")
            self._current_file = open(self._current_file_name, "ab")
        self._current_file.write(binary_data)
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
                loop = asyncio.get_event_loop()
                asyncio.run_coroutine_threadsafe(
                    self._app_state.conversation_service.process_conversation_from_audio(self._current_file_name),
                    loop
                )
            except Exception as e:
                print(f"Error processing session from audio: {e}")

            self._current_file_name = ""
            self._last_utterance_time = None

    async def _check_conversation_timeout(self):
        while True:
            await asyncio.sleep(1)
            if self._current_conversation_id and self._last_utterance_time:
                if (datetime.now() - self._last_utterance_time) > timedelta(seconds=self._conversation_timeout_threshold):
                    await self._close_and_process_current_file()
                    self._current_conversation_id = None
