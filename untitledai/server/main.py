#
# main.py
#
# FastAPI server app. State is stored on the underlying app.state attribute. A peril of this is that
# it breaks IDE type checking so we define a wrapper function to extract app state from FastAPI 
# Request or app objects.
#
# See this discussion: https://github.com/tiangolo/fastapi/issues/504
# We want to attach state to our app that can be explicitly passed in to the app factory function.
# Therefore, we attach it to app.state._app_state and use AppState.get(from_obj=app) to retrieve it.
#

from fastapi import FastAPI

from ..core.config import Configuration
from .app_state import AppState
from .capture import router as capture_router
from .capture_socket import CaptureSocketApp
from ..services import WhisperTranscriptionService, LLMService


def create_server_app(config: Configuration) -> FastAPI:
    # Services
    transcription_service = WhisperTranscriptionService(config=config.transcription)
    llm_service = LLMService(config=config.llm)

    # Create server app
    app = FastAPI()
    app.state._app_state = AppState(
        config=config,
        transcription_service=transcription_service,
        llm_service=llm_service
    )
    socket_app = CaptureSocketApp(app_state = AppState.get(from_obj=app))
    socket_app.mount_to(app=app, at_path="/socket.io")
    app.include_router(capture_router)

    # Base routing
    @app.get("/")
    def read_root():
        return "UntitledAI is running!"

    return app
