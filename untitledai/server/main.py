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
from .conversation_detection import run_conversation_detection_task
from ..services import LLMService, ConversationService, NotificationService
from ..database.database import Database
from ..services.stt.asynchronous.async_transcription_service_factory import AsyncTranscriptionServiceFactory
import ray
import logging
import asyncio
from colorama import init, Fore, Style, Back
from fastapi import Depends

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

#TODO: unify this into a single task queue that takes task objects
async def process_queue(app_state: AppState):
    logger.info("Starting conversation processing queue...")
    while True:
        processed_task = False

        # Conversation detection queue
        while not app_state.conversation_detection_task_queue.empty():
            task = app_state.conversation_detection_task_queue.get()
            #try:
            run_conversation_detection_task(task=task, conversation_task_queue=app_state.conversation_task_queue)
            #except Exception as e:
            #    logging.error(f"Error detecting conversation endpoints: {e}")
            app_state.conversation_detection_task_queue.task_done()
            processed_task = True

        # Conversation processing (transcription, summarization) queue
        while not app_state.conversation_task_queue.empty():
            capture_file, segment_file = app_state.conversation_task_queue.get()
            try:
                await app_state.conversation_service.process_conversation_from_audio(capture_file=capture_file, segment_file=segment_file, voice_sample_filepath=app_state.config.user.voice_sample_filepath, speaker_name=app_state.config.user.name)
            except Exception as e:
                logging.error(f"Error processing conversation: {e}")
            app_state.conversation_task_queue.task_done()
            processed_task = True

        if not processed_task:
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
    notification_service = NotificationService(config.notification)
    conversation_service = ConversationService(config, database, transcription_service, notification_service)
    # Create server app
    app = FastAPI()
    app.state._app_state = AppState(
        config=config,
        database=database,
        conversation_service=conversation_service,
        llm_service=llm_service,
        notification_service=notification_service
    )
    socket_app = CaptureSocketApp(app_state = AppState.get(from_obj=app))
    socket_app.mount_to(app=app, at_path="/socket.io")
    notification_service.socket_app = socket_app
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
    async def read_root(app_state: AppState = Depends(AppState.authenticate_request)):
        return "UntitledAI is running!"

    return app
