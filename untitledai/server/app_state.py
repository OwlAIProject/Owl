from __future__ import annotations  # required for AppState annotation in AppState.get()
from dataclasses import dataclass, field
from typing import Dict
from fastapi import FastAPI, HTTPException, Request, Depends, Header
from typing import Optional
from ..core.config import Configuration
from ..services import CaptureService, ConversationService, LLMService, NotificationService, BingSearchService
from .streaming_capture_handler import StreamingCaptureHandler
from ..database.database import Database
from ..services import ConversationDetectionService
from queue import Queue

@dataclass
class AppState:
    """
    Server application state.
    """

    config: Configuration

    database: Database
    capture_service: CaptureService
    conversation_service: ConversationService
    llm_service: LLMService
    notification_service: NotificationService
    bing_search_service: BingSearchService
    
    capture_handlers: Dict[str, StreamingCaptureHandler] = field(default_factory=lambda: {})
    conversation_detection_service_by_id: Dict[str, ConversationDetectionService] = field(default_factory=lambda: {})

    task_queue = Queue()

    @staticmethod
    def get(from_obj: FastAPI | Request) -> AppState:
        if isinstance(from_obj, FastAPI):
            return from_obj.state._app_state
        elif isinstance(from_obj, Request):
            return from_obj.app.state._app_state
        else:
            raise TypeError("`from_obj` must be of type `FastAPI` or `Request`")
 
    @staticmethod
    def get_db(request: Request):
        app_state: AppState = AppState.get(request)
        return next(app_state.database.get_db())

    @staticmethod
    async def _parse_and_verify_token(authorization: str, expected_token: str):
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header missing")
        
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        token = parts[1]
        if token != expected_token:
            raise HTTPException(status_code=403, detail="Invalid or expired token")

    @staticmethod
    async def authenticate_request(request: Request, authorization: Optional[str] = Header(None)):
        app_state: AppState = AppState.get(request)
        await AppState._parse_and_verify_token(authorization, app_state.config.user.client_token)
        return app_state

    @staticmethod
    async def authenticate_socket(environ: dict):
        headers = {k.decode('utf-8').lower(): v.decode('utf-8') for k, v in environ.get('asgi.scope', {}).get('headers', [])}
        authorization = headers.get('authorization')
        app_state: AppState = AppState.get(environ['asgi.scope']['app'])
        await AppState._parse_and_verify_token(authorization, app_state.config.user.client_token)
        return app_state