#
# capture.py
#
# Capture endpoints: streaming and chunked file uploads via HTTP handled here.
#

import os
from glob import glob
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, UploadFile, Form, Depends
from fastapi.responses import JSONResponse
from pydub import AudioSegment
from starlette.requests import ClientDisconnect
from sqlmodel import Session
import logging
import traceback

from .. import AppState
from ..conversation_detection import submit_conversation_detection_task
from ...database.crud import create_location
from ...files import CaptureFile, append_to_wav_file
from ...models.schemas import Location
from ..streaming_capture_handler import StreamingCaptureHandler
from ...services import ConversationEndpointDetector

logger = logging.getLogger(__name__)

router = APIRouter()

supported_upload_file_extensions = set([ "pcm", "wav", "aac" ])

def find_audio_filepath(audio_directory: str, capture_uuid: str) -> str | None:
    # Files stored as: {audio_directory}/{date}/{device}/{files}.{ext}
    filepaths = glob(os.path.join(audio_directory, "*/*/*"))
    capture_uuids = [ CaptureFile.get_capture_uuid(filepath=filepath) for filepath in filepaths ]
    file_idx = capture_uuids.index(capture_uuid)
    if file_idx < 0:
        return None
    return filepaths[file_idx]

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
            return JSONResponse(content={"message": f"Failed to process because file extension is unsupported: {file_extension}"})

        # Raw PCM is automatically converted to wave format. We do this to prevent client from
        # having to worry about reliability of transmission (in case WAV header chunk is dropped).
        write_wav_header = False
        if file_extension == "pcm":
            file_extension = "wav"
            write_wav_header = True

        # Look up capture session or create a new one
        capture_file: CaptureFile = None
        if capture_uuid in app_state.capture_files_by_id:
            capture_file = app_state.capture_files_by_id[capture_uuid]
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

            # ... and associated conversation endpoint detector
            conversation_endpoint_detector = ConversationEndpointDetector(config=app_state.config, sampling_rate=16000)
            app_state.conversation_endpoint_detectors_by_id[capture_uuid] = conversation_endpoint_detector

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

        # Load audio data
        audio_chunk: AudioSegment = None
        if file_extension == "wav":
            audio_chunk = AudioSegment.from_file(
                file=BytesIO(content),
                sample_width=2, # 16-bit (little endian implied)
                channels=1,
                frame_rate=16000,
                format="pcm"    # pcm/raw
            )
        elif file_extension == "aac":
            audio_chunk = AudioSegment.from_file(
                file=BytesIO(content),
                format="aac"
            )
        else:
            return JSONResponse(content={"message": f"Failed to process because file extension is unsupported: {file_extension}"})

        # Conversation detection and extraction
        submit_conversation_detection_task(app_state=app_state, capture_uuid=capture_uuid, samples=audio_chunk)

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
        
        # Finish the conversation extraction.
        # TODO: If the server dies in the middle of an upload or before /process_capture is called,
        # we will not be able to do this because the in-memory session data will have been lost. A
        # more robust way to handle all this would be to 1) on first chunk, see if any existing file
        # data exists and process it all up to the new chunk and 2) on /process_capture, delete 
        # everything associated with the capture, remove everything from DB, and then regenerate 
        # everything. It is a brute force solution but conceptually simple and should be reasonably
        # robust.
        submit_conversation_detection_task(app_state=app_state, capture_uuid=capture_uuid, samples=None, capture_finished=True)

        # Remove from app state
        if capture_uuid in app_state.capture_files_by_id:
            del app_state.capture_files_by_id[capture_uuid]
        if capture_uuid in app_state.conversation_endpoint_detectors_by_id:
            del app_state.conversation_endpoint_detectors_by_id[capture_uuid]
        
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