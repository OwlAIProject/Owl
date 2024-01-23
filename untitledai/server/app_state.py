from __future__ import annotations  # required for AppState annotation in AppState.get()
from dataclasses import dataclass
from functools import lru_cache
import os

from fastapi import FastAPI, Request

from ..core.config import Configuration
from ..services import ConversationService, LLMService
from ..database.database import Database

@dataclass
class AppState:
    """
    Server application state.
    """

    config: Configuration
    database: Database
    conversation_service: ConversationService
    llm_service: LLMService

    @staticmethod
    def get(from_obj: FastAPI | Request) -> AppState:
        if isinstance(from_obj, FastAPI):
            return from_obj.state._app_state
        elif isinstance(from_obj, Request):
            return from_obj.app.state._app_state
        else:
            raise TypeError("`from_obj` must be of type `FastAPI` or `Request`")

    def _get_audio_directory(self) -> str:
        audio_directory = os.path.join(self.config.captures.capture_dir, "audio")
        os.makedirs(audio_directory, exist_ok=True)
        return audio_directory