#
# capture.py
#
# Capture endpoints: streaming and chunked file uploads via HTTP handled here.
#

import os
from glob import glob
from typing import Annotated

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, UploadFile, Form, Depends
from fastapi.responses import JSONResponse
from starlette.requests import ClientDisconnect
from pydub import AudioSegment
from ...models.schemas import Location
from sqlmodel import Session
from ...database.crud import create_location
import logging
import traceback
from datetime import datetime, timezone

from .. import AppState
from ...files import CaptureFile, create_wav_header, wav_header_size

logger = logging.getLogger(__name__)

router = APIRouter()

def find_audio_filepath(audio_directory: str, capture_id: str) -> str | None:
    # Files stored as: {audio_directory}/{date}/{device}/{files}.{ext}
    filepaths = glob(os.path.join(audio_directory, "*/*/*"))
    capture_ids = [ CaptureFile.get_capture_id(filepath=filepath) for filepath in filepaths ]
    file_idx = capture_ids.index(capture_id)
    if file_idx < 0:
        return None
    return filepaths[file_idx]

supported_upload_file_extensions = set([ "pcm", "aac", "m4a" ])
    
@router.post("/capture/streaming_post/{capture_id}")
async def streaming_post(request: Request, capture_id: str, device_type: str, app_state = Depends(AppState.get_from_request)):
    logger.info('Client connected')
    try:
        capture_file: CaptureFile = None
        if capture_id in app_state.capture_sessions_by_id:
            capture_file = app_state.capture_sessions_by_id[capture_id]
        else:
            # Create new capture session
            capture_file = CaptureFile(
                audio_directory=app_state.get_audio_directory(),
                capture_id=capture_id,
                device_type=device_type,
                timestamp=datetime.now(timezone.utc),
                file_extension="wav"  # Keep WAV extension in CaptureFile
            )
            app_state.capture_sessions_by_id[capture_id] = capture_file

        # Temporary PCM file path
        pcm_file_path = os.path.splitext(capture_file.filepath)[0] + ".pcm"
        file_mode = "ab" if os.path.exists(pcm_file_path) else "wb"

        with open(pcm_file_path, file_mode) as file:
            async for chunk in request.stream():
                file.write(chunk)
                file.flush()

    except ClientDisconnect:
        logger.info(f"Client disconnected while streaming {capture_id}.")

    return JSONResponse(content={"message": f"Audio received"})

@router.post("/capture/streaming_post/{capture_id}/complete")
async def complete_audio(request: Request, background_tasks: BackgroundTasks, capture_id: str, app_state = Depends(AppState.get_from_request)):
    logger.info(f"Completing audio capture for {capture_id}")
    capture_file: CaptureFile = None
    if capture_id in app_state.capture_sessions_by_id:
        capture_file = app_state.capture_sessions_by_id[capture_id]
    else:
        logger.error(f"Capture session not found for ID: {capture_id}")
        raise HTTPException(status_code=500, detail="Internal error: Capture session not found")

    pcm_file_path = os.path.splitext(capture_file.filepath)[0] + ".pcm"
    if not os.path.exists(pcm_file_path):
        raise HTTPException(status_code=404, detail="PCM file not found")

    try:
        audio_data = AudioSegment.from_file(pcm_file_path, format="raw", frame_rate=16000, channels=1, sample_width=2)
        audio_data.export(capture_file.filepath, format="wav")
        os.remove(pcm_file_path)
    except Exception as e:
        logger.error(f"Error processing audio file: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing audio file: {e}")

    logger.info(f"Audio file processed: {capture_file.filepath}")
    background_tasks.add_task(app_state.conversation_service.process_conversation_from_audio, capture_file=capture_file)

    return JSONResponse(content={"message": f"Audio processed"})

@router.post("/capture/upload_chunk")
async def upload_chunk(request: Request,
                       file: UploadFile,
                       capture_id: Annotated[str, Form()],
                       timestamp: Annotated[str, Form()],
                       device_type: Annotated[str, Form()],
                       app_state = Depends(AppState.get_from_request)):
    try:
        # Validate file format
        file_extension = os.path.splitext(file.filename)[1].lstrip(".")
        if file_extension not in supported_upload_file_extensions:
            return JSONResponse(content={"message": f"Failed to process because file extension is unsupported"})

        # Raw PCM is automatically converted to wave format. We do this to prevent client from
        # having to worry about reliability of transmission (in case WAV header chunk is dropped).
        if file_extension == "pcm":
            file_extension = "wav"  

        # Look up capture session or create a new one
        capture_file: CaptureFile = None
        if capture_id in app_state.capture_sessions_by_id:
            capture_file = app_state.capture_sessions_by_id[capture_id]
        else:
            # Create new capture session
            capture_file = CaptureFile(
                audio_directory=app_state.get_audio_directory(),
                capture_id=capture_id,
                device_type=device_type,
                timestamp=timestamp,
                file_extension=file_extension
            )
            app_state.capture_sessions_by_id[capture_id] = capture_file

        # First chunk or are we appending?
        first_chunk = not os.path.exists(path=capture_file.filepath)
        write_mode = "wb" if first_chunk else "r+b"
        
        # Open and write file
        with open(file=capture_file.filepath, mode=write_mode) as fp:
            # Get uploaded bytes
            content = await file.read()
            
            # Write or update the WAV header if needed
            if file_extension == "wav":
                if first_chunk:
                    header = create_wav_header(sample_bytes=len(content), sample_rate=16000)
                    fp.write(header)
                else:
                    fp.seek(0, 2)       # seek to end to get size
                    existing_sample_bytes = fp.tell() - wav_header_size
                    added_sample_bytes = len(content)
                    header = create_wav_header(sample_bytes=existing_sample_bytes + added_sample_bytes, sample_rate=16000)
                    fp.seek(0)          # beginning of file
                    fp.write(header)    # overwrite header with new
                    fp.seek(0, 2)       # to end of file so we can append

            # Append file data 
            bytes_written = fp.write(content)
            logging.info(f"{capture_file.filepath}: {bytes_written} bytes appended")

            # Success
            return JSONResponse(content={"message": f"Audio processed"})

    except Exception as e:
        logging.error(f"Failed to upload chunk: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    
@router.post("/capture/process_capture")
async def process_capture(request: Request, capture_id: Annotated[str, Form()], app_state = Depends(AppState.get_from_request)):
    try:
        filepath = find_audio_filepath(audio_directory=app_state.get_audio_directory(), capture_id = capture_id)
        logger.info(f"Found file to process: {filepath}")
        capture_file = CaptureFile.from_filepath(filepath=filepath)
        if capture_file is None:
            logger.error(f"Filepath does not conform to expected format and cannot be processed: {filepath}")
            raise HTTPException(status_code=500, detail="Internal error: File is incorrectly named on server")
        await app_state.conversation_service.process_conversation_from_audio(capture_file=capture_file)
        logger.info(f"Finished processing conversation: {capture_file.filepath}")
        return JSONResponse(content={"message": "Conversation processed"})
    except Exception as e:
        logger.error(f"Failed to process: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/capture/location")
async def receive_location(location: Location, db: Session = Depends(AppState.get_db)):
    try:
        logger.info(f"Received location: {location}")
        new_location = create_location(db, location)
        return {"message": "Location received", "location_id": new_location.id}
    except Exception as e:
        logger.error(f"Error processing location: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))




    