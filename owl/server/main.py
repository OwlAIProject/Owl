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
from .routes.capture import router as capture_router
from .routes.conversations import router as conversations_router
from .capture_socket import CaptureSocketApp
from .udp_capture_socket import UDPCaptureSocketApp
from ..services import LLMService, CaptureService, ConversationService, NotificationService, BingSearchService
from ..database.database import Database
from ..services.stt.asynchronous.async_transcription_service_factory import AsyncTranscriptionServiceFactory
from .task import Task
import logging
import asyncio
from colorama import init, Fore, Style, Back
from fastapi import Depends
from ..services.stt.streaming.streaming_whisper.streaming_whisper_server import start_streaming_whisper_server
from ..services.stt.asynchronous.async_whisper.async_whisper_transcription_server import start_async_transcription_server

from .streaming_capture_handler import StreamingCaptureHandler

logger = logging.getLogger(__name__)

# TODO: How to handle logging configuration?
class ColorfulLogger(logging.StreamHandler):

    FORMAT = {
        logging.DEBUG: Fore.CYAN + "%(message)s" + Fore.RESET,
        logging.INFO: Fore.GREEN + "%(message)s" + Fore.RESET,
        logging.WARNING: Fore.YELLOW + "%(message)s" + Fore.RESET,
        logging.ERROR: Back.RED + Fore.WHITE + "%(message)s" + Fore.RESET,
        logging.CRITICAL: Back.RED + Fore.YELLOW + "%(message)s" + Fore.RESET,
    }

    def __init__(self):
        logging.StreamHandler.__init__(self)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        self.setFormatter(formatter)

    def format(self, record):
        record.message = record.getMessage()
        string = logging.StreamHandler.format(self, record)
        return ColorfulLogger.FORMAT[record.levelno] % {'message': string}

def setup_logging():
     init(autoreset=True)
     logging.root.setLevel(logging.INFO)
     handler = ColorfulLogger()
     logging.root.addHandler(handler)

async def process_queue(app_state: AppState):
    logger.info("Starting server task processing queue...")
    while True:
        if not app_state.task_queue.empty():
            task: Task = app_state.task_queue.get()
            try:
                await task.run(app_state=app_state)
            except Exception as e:
                logging.error(f"Error processing task: {e}")
            app_state.task_queue.task_done()
        else:
            await asyncio.sleep(1)

def create_server_app(config: Configuration) -> FastAPI:
    setup_logging()
    # Database
    database = Database(config.database)
    # Services
    llm_service = LLMService(config=config.llm)
    transcription_service = AsyncTranscriptionServiceFactory.get_service(config)
    notification_service = NotificationService(config.notification)
    capture_service = CaptureService(config=config, database=database)
    bing_search_service = BingSearchService(config=config.bing) if config.bing else None
    conversation_service = ConversationService(config, database, transcription_service, notification_service, bing_search_service)

    # Create server app
    app = FastAPI()
    app.state._app_state = AppState(
        config=config,
        database=database,
        capture_service=capture_service,
        conversation_service=conversation_service,
        llm_service=llm_service,
        notification_service=notification_service,
        bing_search_service=bing_search_service
    )
    socket_app = CaptureSocketApp(app_state = AppState.get(from_obj=app))
    socket_app.mount_to(app=app, at_path="/socket.io")
    notification_service.socket_app = socket_app
    app.include_router(capture_router)
    app.include_router(conversations_router)

    @app.on_event("startup")
    async def startup_event():
        # Initialize the database
        app.state._app_state.database.init_db()
        asyncio.create_task(process_queue(app.state._app_state))
        if config.streaming_transcription.provider == "whisper":
            start_streaming_whisper_server(config=config.streaming_whisper)

        if config.async_transcription.provider == "whisper":
            start_async_transcription_server(config=config.async_whisper)

        # UPD capture for LTE-M and other low bandwidth devices
        if config.udp.enabled:
            loop = asyncio.get_running_loop()
            await loop.create_datagram_endpoint(
                lambda: UDPCaptureSocketApp(app.state._app_state), local_addr=(config.udp.host, config.udp.port)
            )
        # fail any conversations that were in progress if the server was not shut down gracefully. could also retry them
        await conversation_service.fail_processing_and_capturing_conversations()

    @app.on_event("shutdown")
    async def shutdown_event():
        conversation_service = app.state._app_state.conversation_service
        await conversation_service.fail_processing_and_capturing_conversations()

    # Base routing
    @app.get("/")
    async def read_root(app_state: AppState = Depends(AppState.authenticate_request)):
        return "Owl is running!"

    return app
