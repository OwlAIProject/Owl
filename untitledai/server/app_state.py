from __future__ import annotations  # required for AppState annotation in AppState.get()
from dataclasses import dataclass, field
import os
from typing import Dict

from fastapi import FastAPI, Request

from ..core.config import Configuration
from ..services import ConversationService, LLMService
from .streaming_capture_handler import StreamingCaptureHandler
from ..database.database import Database
from ..files import CaptureFile
from queue import Queue

@dataclass
class AppState:
    """
    Server application state.
    """

    config: Configuration

    database: Database
    conversation_service: ConversationService
    llm_service: LLMService
    
    capture_sessions_by_id: Dict[str, CaptureFile] = field(default_factory=lambda: {})
    capture_handlers: Dict[str, StreamingCaptureHandler] = field(default_factory=lambda: {})

    conversation_task_queue = Queue()

    @staticmethod
    def get(from_obj: FastAPI | Request) -> AppState:
        if isinstance(from_obj, FastAPI):
            return from_obj.state._app_state
        elif isinstance(from_obj, Request):
            return from_obj.app.state._app_state
        else:
            raise TypeError("`from_obj` must be of type `FastAPI` or `Request`")
        
    @staticmethod
    def get_from_request(request: Request) -> AppState:
            return request.app.state._app_state  
    
    @staticmethod
    def get_db(request: Request):
        app_state: AppState = AppState.get(request)
        return next(app_state.database.get_db())

    def get_audio_directory(self) -> str:
        audio_directory = os.path.join(self.config.captures.capture_dir, "audio")
        os.makedirs(audio_directory, exist_ok=True)
        return audio_directory

  