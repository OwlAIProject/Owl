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
from ..services import LLMService
from ..services import ConversationService
from ..database.database import Database
from ..services.stt.asynchronous.async_transcription_service_factory import AsyncTranscriptionServiceFactory
import ray
import logging
import asyncio
from colorama import init, Fore, Style, Back

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
    logger.info("Starting conversation processing queue...")
    while True:
        if not app_state.conversation_task_queue.empty():
            capture_file, segment_file = app_state.conversation_task_queue.get()
            try:
                await app_state.conversation_service.process_conversation_from_audio(capture_file, segment_file)
            except Exception as e:
                logging.error(f"Error processing conversation: {e}")
            app_state.conversation_task_queue.task_done()
        else:
            await asyncio.sleep(1)

def running_local_models(config: Configuration):
    return config.async_transcription.provider == "whisper"

def create_server_app(config: Configuration) -> FastAPI:
    setup_logging()
    # Database
    database = Database(config.database)
    # Services
    llm_service = LLMService(config=config.llm)
    transcription_service = AsyncTranscriptionServiceFactory.get_service(config)
    conversation_service = ConversationService(config, database, transcription_service)

    # Create server app
    app = FastAPI()
    app.state._app_state = AppState(
        config=config,
        database=database,
        conversation_service=conversation_service,
        llm_service=llm_service
    )
    socket_app = CaptureSocketApp(app_state = AppState.get(from_obj=app))
    socket_app.mount_to(app=app, at_path="/socket.io")
    app.include_router(capture_router)
    app.include_router(conversations_router)

    @app.on_event("startup")
    async def startup_event():
        if not ray.is_initialized() and running_local_models(config):
            ray.init()
        # Initialize the database
        app.state._app_state.database.init_db()
        asyncio.create_task(process_queue(app.state._app_state))

    @app.on_event("shutdown")
    async def shutdown_event():
        if ray.is_initialized():
            ray.shutdown()
            
    # Base routing
    @app.get("/")
    def read_root():
        return "UntitledAI is running!"

    return app
