#
# capture.py
#
# Capture endpoints: streaming and chunked file uploads via HTTP handled here.
#

import os
from glob import glob
import shutil
from typing import Annotated
import uuid

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, UploadFile, Form, Depends
from fastapi.responses import JSONResponse
from starlette.requests import ClientDisconnect
from sqlmodel import Session
import logging
import traceback

from .. import AppState
from ...database.crud import create_location
from ...files import CaptureFile, append_to_wav_file
from ...models.schemas import Location
from ..streaming_capture_handler import StreamingCaptureHandler

logger = logging.getLogger(__name__)

router = APIRouter()

def find_audio_filepath(audio_directory: str, capture_uuid: str) -> str | None:
    # Files stored as: {audio_directory}/{date}/{device}/{files}.{ext}
    filepaths = glob(os.path.join(audio_directory, "*/*/*"))
    capture_uuids = [ CaptureFile.get_capture_uuid(filepath=filepath) for filepath in filepaths ]
    file_idx = capture_uuids.index(capture_uuid)
    if file_idx < 0:
        return None
    return filepaths[file_idx]

supported_upload_file_extensions = set([ "pcm", "wav", "aac", "m4a" ])

@router.post("/capture/streaming_post/{capture_uuid}")
async def streaming_post(request: Request, capture_uuid: str, device_type: str, app_state: AppState = Depends(AppState.authenticate_request)):
    logger.info('Client connected')
    try:
        if capture_uuid not in app_state.capture_handlers:
            app_state.capture_handlers[capture_uuid] = StreamingCaptureHandler(
                app_state, device_type, capture_uuid, file_extension = "wav", stream_format={
                    "sample_rate": 16000,
                    "encoding": "linear16"
                }
            )

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

@router.post("/capture/upload_chunk")
async def upload_chunk(request: Request,
                       file: UploadFile,
                       capture_uuid: Annotated[str, Form()],
                       timestamp: Annotated[str, Form()],
                       device_type: Annotated[str, Form()],
                       app_state: AppState = Depends(AppState.authenticate_request)):
    try:
        # Validate file format
        file_extension = os.path.splitext(file.filename)[1].lstrip(".")
        if file_extension not in supported_upload_file_extensions:
            return JSONResponse(content={"message": f"Failed to process because file extension is unsupported"})

        # Raw PCM is automatically converted to wave format. We do this to prevent client from
        # having to worry about reliability of transmission (in case WAV header chunk is dropped).
        write_wav_header = False
        if file_extension == "pcm":
            file_extension = "wav"
            write_wav_header = True

        # Look up capture session or create a new one
        capture_file: CaptureFile = None
        if capture_uuid in app_state.capture_sessions_by_id:
            capture_file = app_state.capture_sessions_by_id[capture_uuid]
        else:
            # Create new capture session
            capture_file = CaptureFile(
                capture_directory=app_state.config.captures.capture_dir,
                capture_uuid=capture_uuid,
                device_type=device_type,
                timestamp=timestamp,
                file_extension=file_extension
            )
            app_state.capture_sessions_by_id[capture_uuid] = capture_file

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
        
        # For now, endpointing not hooked up, so process this as one big conversation by creating a
        # single segment out of it
        segment_file = capture_file.create_conversation_segment(
            conversation_uuid=uuid.uuid1().hex,
            timestamp=capture_file.timestamp,
            file_extension=os.path.splitext(capture_file.filepath)[1]
        )
        shutil.copy2(src=capture_file.filepath, dst=segment_file.filepath)

        # Enqueue for processing
        task = (capture_file, segment_file)
        app_state.conversation_task_queue.put(task)
        
        logger.info(f"Enqueued conversation capture for processing: {segment_file.filepath}")
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
        return {"message": "Location received", "location_id": new_location.id}
    except Exception as e:
        logger.error(f"Error processing location: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))