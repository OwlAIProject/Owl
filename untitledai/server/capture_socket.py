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
from ..services.endpointing.streaming.streaming_endpointing_service import StreamingEndpointingService
from ..files import CaptureFile
from ..database.crud import get_conversation
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

    async def on_connect(self, path, sid, *args):
        logger.info(f'Connected: {sid}')

    async def on_disconnect(self, path, sid, *args):
        logger.info(f'Disconnected: {sid}')

    async def on_audio_data(self, path, sid, binary_data, device_name, capture_id, *args):
        if capture_id not in self._app_state.capture_handlers:
            self._app_state.capture_handlers[capture_id] = StreamingCaptureHandler(
                self._app_state, device_name, capture_id
            )

        capture_handler = self._app_state.capture_handlers[capture_id]

        await capture_handler.handle_audio_data(binary_data)

    async def on_finish_audio(self, path, sid, capture_id, *args):
        logger.info(f"Client signalled end of audio stream for {capture_id}")
        if capture_id not in self._app_state.capture_handlers:
            logger.error(f"Capture session not found: {capture_id}")
            return
        capture_handler = self._app_state.capture_handlers[capture_id]
        capture_handler.finish_capture_session()
