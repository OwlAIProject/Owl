#
# capture.py
#
# Capture endpoints: streaming and chunked file uploads via HTTP handled here.
#
# TODO
# ----
# - Capture socket to use same endpointing mechanism (ConversationDetectionService).
# - Can we unify with streaming code by having chunking simply forward there via socket?
#

from datetime import datetime
import os
from typing import Annotated

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, UploadFile, Form, Depends, File
from fastapi.responses import JSONResponse
from starlette.requests import ClientDisconnect
from sqlmodel import Session

import logging
import traceback
from datetime import datetime, timezone

from .. import AppState
from ..task import Task
from ...database.crud import create_location, update_latest_conversation_location, get_capture_file_ref, get_latest_capturing_conversation_by_capture_uuid, create_image
from ...files import append_to_wav_file
from ...models.schemas import Location, Capture, ConversationRead, Image
from ..streaming_capture_handler import StreamingCaptureHandler
from ...services import ConversationDetectionService
from ...files.capture_directory import CaptureDirectory



logger = logging.getLogger(__name__)

router = APIRouter()

####################################################################################################
# Image API
####################################################################################################

@router.post("/capture/image")
async def upload_image(
    file: UploadFile = File(...),
    capture_uuid: str = Form(...),
    app_state: AppState = Depends(AppState.authenticate_request),
    db: Session = Depends(AppState.get_db),
    ):
    capture = get_capture_file_ref(db, capture_uuid)
    if not capture:
        raise HTTPException(status_code=404, detail="Capture not found")
    conversation = get_latest_capturing_conversation_by_capture_uuid(db, capture_uuid)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    timestamp = datetime.now(timezone.utc)
    extension = os.path.splitext(file.filename)[1]
    filepath = CaptureDirectory(config=app_state.config).get_image_filepath(capture_file=capture, conversation_uuid=conversation.conversation_uuid, timestamp=timestamp, extension=extension)
    with open(filepath, "wb+") as file_object:
        file_object.write(await file.read())
    image = Image(
        filepath=filepath,
        conversation_uuid=conversation.conversation_uuid,
        capture_uuid=capture_uuid,
        captured_at=timestamp,
        source_capture_id=capture.id,
        conversation_id=conversation.id
    )
    create_image(db, image)
    return JSONResponse(status_code=200, content={"message": f"File '{file.filename}' saved.'"})

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
        capture_file: Capture,
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

        # As soon as we detect a new, in-progress conversation, we need to create a conversation
        # object in the database and create a segment file object for it.
        active_convo = detection_results.in_progress
        if active_convo is not None and app_state.conversation_service.get_conversation(conversation_uuid=active_convo.uuid) is None:
            # Create the conversation (and transcript), and references to the capture and segment
            # files in db. This will also send a notification to app of a new conversation. Note
            # that the segment file is not yet created on disk (will happen once the conversation)
            # is actually finished. For chunked uploads, we do not do any partial transcription or
            # otherwise process the conversation until it is known to be complete!
            await app_state.conversation_service.create_conversation(
                conversation_uuid=active_convo.uuid,
                start_time=active_convo.endpoints.start,
                capture_file=capture_file
            )

        #TODO: how to update conversation-in-progress after it has been created? Need to send some
        # sort of notification to UI to let it know latest progress.

        # Handle the completed conversations. Two things have to happen here:
        #
        # 1. Because chunks can be arbitrarily long, it is possible that conversations are detected
        #    and completed for the first time here. That is, we may have conversations that we
        #    we never saw "in progress". Therefore, we have to create the objects if need-be.
        # 2. Now that we know where the conversations have ended, we can ask the detection service
        #    to extract them into their designated segment file locations in one shot.
        completed_conversations = []
        conversation_filepaths = []
        for convo in detection_results.completed:
            if app_state.conversation_service.get_conversation(conversation_uuid=convo.uuid) is None:
                # First time we've encountered this conversation. Need to create a new conversation
                # and enter it into the database.
                await app_state.conversation_service.create_conversation(
                    conversation_uuid=convo.uuid,
                    start_time=convo.endpoints.start,
                    capture_file=capture_file
                )

            # We now know the conversation segment exists, add it to the list of conversations to
            # process.
            completed_conversations.append(app_state.conversation_service.get_conversation(conversation_uuid=convo.uuid))
            conversation_filepaths.append(completed_conversations[-1].capture_segment_file.filepath)

        # Perform the extraction!
        await detection_service.extract_conversations(conversations=detection_results.completed, conversation_filepaths=conversation_filepaths)

        # Process each completed conversation
        try:
            for conversation in completed_conversations:
                # We just need to pass the uuid since the conversation is already persisted
                await app_state.conversation_service.process_conversation_from_audio(conversation_uuid=conversation.conversation_uuid)
        except Exception as e:
            logging.error(f"Error processing conversation: {e}")

Task.register(ProcessAudioChunkTask)

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
            raise HTTPException(status_code=500, detail=f"Failed to process because file extension is unsupported: {file_extension}")

        # Validate timestamp
        try:
            start_time = datetime.strptime(timestamp, "%Y%m%d-%H%M%S.%f")
        except:
            raise HTTPException(status_code=500, detail="'timestamp' string does not conform to YYYYmmdd-HHMMSS.fff format")

        # Raw PCM is automatically converted to wave format. We do this to prevent client from
        # having to worry about reliability of transmission (in case WAV header chunk is dropped).
        write_wav_header = False
        if file_extension == "pcm":
            file_extension = "wav"
            write_wav_header = True

        # Look up capture session or create a new one
        capture_file: Capture = app_state.capture_service.get_capture_file(capture_uuid=capture_uuid)
        if capture_file is None:
            capture_file = app_state.capture_service.create_capture_file(
                capture_uuid=capture_uuid,
                format=file_extension,
                start_time=start_time,
                device_type=device_type
            )

        # Ensure a conversation detection service has been created
        detection_service: ConversationDetectionService = app_state.conversation_detection_service_by_id.get(capture_uuid)
        if detection_service is None:
            detection_service = ConversationDetectionService(
                config=app_state.config,
                capture_filepath=capture_file.filepath,
                capture_timestamp=capture_file.start_time
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
        capture_file: Capture = app_state.capture_service.get_capture_file(capture_uuid=capture_uuid)
        if capture_file is None:
            logger.error(f"Capture file for capture_uuid={capture_uuid} not found! Cannot process capture.")
            raise HTTPException(status_code=500, detail=f"Capture file for capture_uuid={capture_uuid} not found! Cannot process capture.")

        # TODO: If the server dies in the middle of an upload or before /process_capture is called,
        # this will not work well because the in-memory conversation detection state will be gone.
        # However, users can protentially re-process the conversation manually.

        # Conversation detection service
        detection_service: ConversationDetectionService = app_state.conversation_detection_service_by_id.get(capture_uuid)
        if detection_service is None:
            logger.error(f"Internal error: No conversation detection service exists for capture_uuid={capture_uuid}")
            raise HTTPException(status_Code=500, detail="Internal error: Lost conversation service")

        # Enqueue for processing
        task = ProcessAudioChunkTask(
            capture_file=capture_file,
            detection_service=detection_service,
            format=os.path.splitext(capture_file.filepath)[1].lstrip(".")
        )
        app_state.task_queue.put(task)

        # Remove from in-memory app state
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
