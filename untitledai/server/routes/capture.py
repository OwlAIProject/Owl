#
# capture.py
#
# Capture endpoints: streaming and chunked file uploads via HTTP handled here.
#

from datetime import datetime, timedelta, timezone
from glob import glob
import os
from typing import Annotated
import uuid
import asyncio

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, UploadFile, Form, Depends
from fastapi.responses import JSONResponse
from starlette.requests import ClientDisconnect
from sqlmodel import Session
import logging
import traceback

from .. import AppState
from ..task import Task
from ...database.crud import create_location, get_capture_file_segment_file_ref, update_latest_conversation_location
from ...files import CaptureFile, append_to_wav_file
from ...models.schemas import Location, ConversationRead
from ..streaming_capture_handler import StreamingCaptureHandler
from ...services import ConversationDetectionService


logger = logging.getLogger(__name__)

router = APIRouter()


####################################################################################################
# Stream API
####################################################################################################

@router.post("/capture/streaming_post/{capture_uuid}")
async def streaming_post(request: Request, capture_uuid: str, device_type: str, app_state: AppState = Depends(AppState.authenticate_request)):
    logger.info('Client connected')
    try:
        if capture_uuid not in app_state.capture_handlers:
            app_state.capture_handlers[capture_uuid] = StreamingCaptureHandler(app_state, device_type, capture_uuid, file_extension = "wav")

        capture_handler = app_state.capture_handlers[capture_uuid]

        async for chunk in request.stream():
            await capture_handler.handle_audio_data(chunk)

    except ClientDisconnect:
        logger.info(f"Client disconnected while streaming {capture_uuid}.")

    return JSONResponse(content={"message": f"Audio received"})


@router.post("/capture/streaming_post/{capture_uuid}/complete")
async def complete_audio(request: Request, background_tasks: BackgroundTasks, capture_uuid: str, app_state: AppState = Depends(AppState.authenticate_request)):
    logger.info(f"Completing audio capture for {capture_uuid}")
    if capture_uuid not in app_state.capture_handlers:
        logger.error(f"Capture session not found: {capture_uuid}")
        raise HTTPException(status_code=500, detail="Capture session not found")
    capture_handler = app_state.capture_handlers[capture_uuid]
    capture_handler.finish_capture_session()

    return JSONResponse(content={"message": f"Audio processed"})


####################################################################################################
# Chunk API
####################################################################################################

supported_upload_file_extensions = set([ "pcm", "wav", "aac" ])

class ProcessAudioChunkTask(Task):
    """
    Processes the newest chunk of audio in a capture. Detects conversations incrementally and
    processes any that are found.
    """

    def __init__(
        self,
        capture_file: CaptureFile,
        detection_service: ConversationDetectionService,
        format: str,
        audio_data: bytes | None = None
    ):
        self._capture_file = capture_file
        self._detection_service = detection_service
        self._audio_data = audio_data
        self._format = format
        assert format == "wav" or format == "aac"

    async def run(self, app_state: AppState):
        # Data we need
        capture_file = self._capture_file
        audio_data = self._audio_data
        capture_finished = audio_data is None
        format = self._format
        detection_service = self._detection_service
        
        # Run conversation detection stage (finds conversations thus far)
        detection_results = await detection_service.detect_conversations(audio_data=audio_data, format=format, capture_finished=capture_finished)

        convo_filepaths = []
        completed_conversation_uuid = []
        for convo in detection_results.completed:
            # get the file path since it was persisted when the conversation was created
            with next(app_state.database.get_db()) as db:
                segment_file_ref = get_capture_file_segment_file_ref(db, convo.uuid)
                convo_filepaths.append(segment_file_ref.file_path)
            completed_conversation_uuid.append(convo.uuid)
        await detection_service.extract_conversations(conversations=detection_results.completed, conversation_filepaths=convo_filepaths)

        # Process each completed conversation
        try:
            for conversation_uuid in completed_conversation_uuid:
                # we just need to pass the uuid since the conversation is already persisted
                await app_state.conversation_service.process_conversation_from_audio(conversation_uuid=conversation_uuid)
        except Exception as e:
            logging.error(f"Error processing conversation: {e}")

        conversation_in_progress = detection_results.in_progress
        if conversation_in_progress is not None:
            segment_file = capture_file.create_conversation_segment(
                conversation_uuid=conversation_in_progress.uuid,
                timestamp=conversation_in_progress.endpoints.start,
                file_extension=format
            )
            # create the conversation which will also create the persisted capture file and capture segment file
            await app_state.conversation_service.create_conversation(capture_file=capture_file, segment_file=segment_file)
            
Task.register(ProcessAudioChunkTask)

def find_audio_filepath(audio_directory: str, capture_uuid: str) -> str | None:
    # Files stored as: {audio_directory}/{date}/{device}/{files}.{ext}
    filepaths = glob(os.path.join(audio_directory, "*/*/*"))
    capture_uuids = [ CaptureFile.get_capture_uuid(filepath=filepath) for filepath in filepaths ]
    file_idx = capture_uuids.index(capture_uuid)
    if file_idx < 0:
        return None
    return filepaths[file_idx]

@router.post("/capture/upload_chunk")
async def upload_chunk(
    request: Request,
    file: UploadFile,
    capture_uuid: Annotated[str, Form()],
    timestamp: Annotated[str, Form()],
    device_type: Annotated[str, Form()],
    app_state: AppState = Depends(AppState.authenticate_request)
):
    try:
        # Validate file format
        file_extension = os.path.splitext(file.filename)[1].lstrip(".")
        if file_extension not in supported_upload_file_extensions:
            return JSONResponse(content={"message": f"Failed to process because file extension is unsupported: {file_extension}"})

        # Raw PCM is automatically converted to wave format. We do this to prevent client from
        # having to worry about reliability of transmission (in case WAV header chunk is dropped).
        write_wav_header = False
        if file_extension == "pcm":
            file_extension = "wav"
            write_wav_header = True

        # Look up capture session or create a new one
        capture_file: CaptureFile = None
        detection_service: ConversationDetectionService = None
        if capture_uuid in app_state.capture_files_by_id:
            capture_file = app_state.capture_files_by_id[capture_uuid]
            detection_service = app_state.conversation_detection_service_by_id.get(capture_uuid)
            if detection_service is None:
                logger.error(f"Internal error: No conversation detection service exists for capture_uuid={capture_uuid}")
                raise HTTPException(status_code=500, detail="Internal error: Lost conversation service")
        else:
            # Create new capture session
            capture_file = CaptureFile(
                capture_directory=app_state.config.captures.capture_dir,
                capture_uuid=capture_uuid,
                device_type=device_type,
                timestamp=timestamp,
                file_extension=file_extension
            )
            app_state.capture_files_by_id[capture_uuid] = capture_file

            # ... and associated conversation detection service
            detection_service = ConversationDetectionService(
                config=app_state.config,
                capture_filepath=capture_file.filepath,
                capture_timestamp=capture_file.timestamp
            )
            app_state.conversation_detection_service_by_id[capture_uuid] = detection_service
        
        # Get uploaded data
        content = await file.read()
        
        # Append to file
        bytes_written = 0
        if write_wav_header:
            bytes_written = append_to_wav_file(filepath=capture_file.filepath, sample_bytes=content, sample_rate=16000)
        else:
            with open(file=capture_file.filepath, mode="ab") as fp:
                bytes_written = fp.write(content)
        logging.info(f"{capture_file.filepath}: {bytes_written} bytes appended")

        # Conversation processing task
        task = ProcessAudioChunkTask(
            capture_file=capture_file,
            detection_service=detection_service,
            audio_data=content,
            format=file_extension
        )
        app_state.task_queue.put(task)

        # Success
        return JSONResponse(content={"message": f"Audio processed"})

    except Exception as e:
        logging.error(f"Failed to upload chunk: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    
@router.post("/capture/process_capture")
async def process_capture(request: Request, capture_uuid: Annotated[str, Form()], app_state: AppState = Depends(AppState.authenticate_request)):
    try:
        # Get capture file
        filepath = find_audio_filepath(audio_directory=app_state.config.captures.capture_dir, capture_uuid=capture_uuid)
        logger.info(f"Found file to process: {filepath}")
        capture_file: CaptureFile = CaptureFile.from_filepath(filepath=filepath)
        if capture_file is None:
            logger.error(f"Filepath does not conform to expected format and cannot be processed: {filepath}")
            raise HTTPException(status_code=500, detail="Internal error: File is incorrectly named on server")
        
        # Conversation detection service
        detection_service: ConversationDetectionService = app_state.conversation_detection_service_by_id.get(capture_uuid)
        if detection_service is None:
            logger.error(f"Internal error: No conversation detection service exists for capture_uuid={capture_uuid}")
            raise HTTPException(status_Code=500, detail="Internal error: Lost conversation service")
        
        # Finish the conversation extraction.
        # TODO: If the server dies in the middle of an upload or before /process_capture is called,
        # we will not be able to do this because the in-memory session data will have been lost. A
        # more robust way to handle all this would be to 1) on first chunk, see if any existing file
        # data exists and process it all up to the new chunk and 2) on /process_capture, delete 
        # everything associated with the capture, remove everything from DB, and then regenerate 
        # everything. It is a brute force solution but conceptually simple and should be reasonably
        # robust.
        # Conversation processing task
        task = ProcessAudioChunkTask(
            capture_file=capture_file,
            detection_service=detection_service,
            format=os.path.splitext(capture_file.filepath)[1].lstrip(".")
        )
        app_state.task_queue.put(task)

        # Remove from app state
        if capture_uuid in app_state.capture_files_by_id:
            del app_state.capture_files_by_id[capture_uuid]
        if capture_uuid in app_state.conversation_detection_service_by_id:
            del app_state.conversation_detection_service_by_id[capture_uuid]
        
        return JSONResponse(content={"message": "Conversation processed"})
    except Exception as e:
        logger.error(f"Failed to process: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/capture/location")
async def receive_location(location: Location, db: Session = Depends(AppState.get_db), app_state: AppState = Depends(AppState.authenticate_request)):
    try:
        logger.info(f"Received location: {location}")
        new_location = create_location(db, location)
        if location.capture_uuid:
            conversation = update_latest_conversation_location(db, location.capture_uuid, location)
            await app_state.notification_service.emit_message("update_conversation",  ConversationRead.from_orm(conversation).model_dump_json())
            
        return {"message": "Location received", "location_id": new_location.id}
    except Exception as e:
        logger.error(f"Error processing location: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
