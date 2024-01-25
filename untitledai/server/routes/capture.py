#
# capture.py
#
# Capture endpoints: streaming and chunked file uploads via HTTP handled here.
#

import os

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, UploadFile, Depends
from fastapi.responses import JSONResponse
from starlette.requests import ClientDisconnect
from pydub import AudioSegment
from ...models.schemas import Location
from sqlmodel import Session
from ...database.crud import create_location
import logging
import traceback

from .. import AppState
from ...devices import DeviceType
from ..capture import CaptureSession, create_wav_header, wav_header_size

logger = logging.getLogger(__name__)

router = APIRouter()

def get_database(request: Request):
    app_state: AppState = AppState.get(request)
    return app_state.database.get_db()

supported_upload_file_extensions = set([ "pcm", "aac", "m4a" ])
    
@router.post("/capture/streaming_post/{unique_id}")
async def streaming_post(request: Request, unique_id: str):
    logger.info('Client connected')
    state = AppState.get(from_obj=request)
    file_path = os.path.join(state.get_audio_directory(), f"{unique_id}.pcm")
    file_mode = "ab" if os.path.exists(file_path) else "wb"

    try:
        with open(file_path, file_mode) as file:
            async for chunk in request.stream():
                file.write(chunk)
                file.flush()
    except ClientDisconnect:
        logger.info(f"Client disconnected while streaming {unique_id}.")

    return JSONResponse(content={"message": f"Audio received"})

@router.post("/capture/streaming_post/{unique_id}/complete")
async def complete_audio(request: Request, background_tasks: BackgroundTasks, unique_id: str):
    state = AppState.get(from_obj=request)
    pcm_file_name = os.path.join(state.get_audio_directory(), f"{unique_id}.pcm")
    if not os.path.exists(pcm_file_name):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        audio_data = AudioSegment.from_file(pcm_file_name, format="raw", frame_rate=48000, channels=1, sample_width=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing audio file: {e}")
    
    wave_file_name = ".".join(pcm_file_name.split(".")[:-1]) + ".wav"

    audio_data.export(wave_file_name, format="wav")
    os.remove(pcm_file_name)
    # background_tasks.add_task(process_session_from_audio, state.transcription_service, state.llm_service, wave_file_name)

    return JSONResponse(content={"message": f"Audio processed"})

@router.post("/capture/upload_chunk")
async def upload_chunk(request: Request, file: UploadFile, session_id: str, timestamp: str, device_type: str):
    try:
        app_state: AppState = AppState.get(from_obj=request)

        # Look up session or create a new one
        session: CaptureSession = None
        if session_id in app_state.capture_sessions_by_id:
            session = app_state.capture_sessions_by_id[session_id]
        else:
            # Validate file format
            file_extension = os.path.splitext(file.filename)[1].lstrip(".")
            if file_extension not in supported_upload_file_extensions:
                return JSONResponse(content={"message": f"Failed to process because file extension is unsupported"})

            # Raw PCM is automatically converted to wave format. We do this to prevent client from
            # having to worry about reliability of transmission (in case WAV header chunk is dropped).
            if file_extension == "pcm":
                file_extension = "wav"

            # Create new session
            session = CaptureSession(
                audio_directory=app_state.get_audio_directory(),
                session_id=session_id,
                device_type=DeviceType(device_type) if hasattr(DeviceType, device_type) else DeviceType.UNKNOWN,
                timestamp=timestamp,
                file_extension=file_extension
            )
            app_state.capture_sessions_by_id[session_id] = session

        # First chunk or are we appending?
        first_chunk = not os.path.exists(path=session.filepath)
        write_mode = "wb" if first_chunk else "r+b"
        
        # Open and write file
        with open(file=session.filepath, mode=write_mode) as fp:
            # Get uploaded bytes
            content = await file.read()
            
            # Write or update the WAV header if needed
            if file_extension == "wav":
                if first_chunk:
                    header = create_wav_header(sample_bytes=len(content), sample_rate=16000)
                    await fp.write(header)
                else:
                    fp.seek(0, 2)       # seek to end to get size
                    existing_sample_bytes = await fp.tell() - wav_header_size
                    added_sample_bytes = len(content)
                    header = create_wav_header(sample_bytes=existing_sample_bytes + added_sample_bytes, sample_rate=16000)
                    fp.seek(0)          # beginning of file
                    fp.write(header)    # overwrite header with new
                    fp.seek(0, 2)       # to end of file so we can append

            # Append file data 
            bytes_written = fp.write(content)
            print(f"{session.filepath}: {bytes_written} bytes appended")

    except Exception as e:
        return JSONResponse(content={"message": f"Failed to process: {e}"})

    
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




    