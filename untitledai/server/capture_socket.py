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
from fastapi import FastAPI
import socketio

from .streaming_capture_handler import StreamingCaptureHandler

logger = logging.getLogger(__name__)

class CaptureSocketApp(socketio.AsyncNamespace):
    def __init__(self, app_state):
        super().__init__(namespace="*")
        self._app_state = app_state
        self._sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
        self._app = socketio.ASGIApp(self._sio)
        self._sio.register_namespace(self)
        self._processing_task = None

    def mount_to(self, app: FastAPI, at_path: str):
        app.mount(path=at_path, app=self._app)

    async def on_connect(self, path, sid, environ):
        logger.info(f'Connected: {sid}')
        try:
            await self._app_state.authenticate_socket(environ)
        except ValueError as e:
            logger.error(f"Authentication failed for {sid}: {e}")
            await self._sio.disconnect(sid)
            return False 

    async def on_disconnect(self, path, sid, *args):
        logger.info(f'Disconnected: {sid}')

    async def on_audio_data(self, path, sid, binary_data, device_name, capture_uuid, file_extension="aac", *args):
        if capture_uuid not in self._app_state.capture_handlers:
            self._app_state.capture_handlers[capture_uuid] = StreamingCaptureHandler(
                self._app_state, device_name, capture_uuid, file_extension
            )

        capture_handler = self._app_state.capture_handlers[capture_uuid]

        await capture_handler.handle_audio_data(binary_data)

    async def on_finish_audio(self, path, sid, capture_uuid, *args):
        logger.info(f"Client signalled end of audio stream for {capture_uuid}")
        if capture_uuid not in self._app_state.capture_handlers:
            logger.error(f"Capture session not found: {capture_uuid}")
            return
        capture_handler = self._app_state.capture_handlers[capture_uuid]
        capture_handler.finish_capture_session()
    
    async def emit_message(self, event, message):
        print(f"emit_message message: {event} {message}")
        await self._sio.emit(event, message)
