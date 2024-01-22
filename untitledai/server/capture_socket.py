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
from datetime import datetime

from fastapi import FastAPI
import socketio

from ..server import AppState
from .process_session import process_session_from_audio


class CaptureSocketApp(socketio.AsyncNamespace):
    def __init__(self, app_state: AppState):
        super(CaptureSocketApp, self).__init__(namespace="*")   # socketio.AsyncNamesapce(namespace="*")

        self._app_state = app_state

        self._sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
        self._app = socketio.ASGIApp(self._sio)
        self._sio.register_namespace(namespace_handler=self)

        self._current_file = None
        self._current_file_name = ""
        self._last_audio_time = None
        self._file_timeout_task = None
        self.audio_directory = self._app_state._get_audio_directory()
        
    def mount_to(self, app: FastAPI, at_path: str):
        app.mount(path=at_path, app=self._app)
    
    async def on_connect(self, path, sid, *args):
        print('Connected: ', sid)
    
    async def on_disconnect(self, path, sid, *args):
        print('Disconnected: ', sid)

    async def on_audio_data(self, path, sid, binary_data):
        if not self._current_file:
            self._current_file_name = os.path.join(self.audio_directory, f"audio_{datetime.now().strftime('%Y%m%d%H%M%S')}.aac")
            self._current_file = open(self._current_file_name, "ab")
            self._last_audio_time = asyncio.get_event_loop().time()
            if self._file_timeout_task:
                self._file_timeout_task.cancel()
            self._file_timeout_task = asyncio.create_task(self._file_timeout())
        self._current_file.write(binary_data)
        self._last_audio_time = asyncio.get_event_loop().time()
    
    async def on_finish_audio(self, path, sid):
        await self._close_and_process_file()
    
    async def _file_timeout(self):
        while self._current_file and (asyncio.get_event_loop().time() - self._last_audio_time) <= 10:
            await asyncio.sleep(1)
        if self._current_file:
            print(f"File {self._current_file_name} closed due to timeout.")
            await self._close_and_process_file()

    async def _close_and_process_file(self):
        if self._current_file:
            self._current_file.close()
            self._current_file = None
            print(f"File {self._current_file_name} closed.")

            try:
                await process_session_from_audio(
                    transcription_service=self._app_state.transcription_service,
                    llm_service=self._app_state.llm_service,
                    capture_filepath=self._current_file_name
                )
            except Exception as e:
                print(f"Error processing session from audio: {e}")