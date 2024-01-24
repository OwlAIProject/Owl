#
# capture.py
#
# Capture endpoints: streaming and chunked file uploads via HTTP handled here.
#

import os

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from starlette.requests import ClientDisconnect
from pydub import AudioSegment

from ..server import AppState
from .process_session import process_session_from_audio

router = APIRouter()
    
@router.post("/capture/streaming_post/{unique_id}")
async def streaming_post(request: Request, unique_id: str):
    print('Client connected')
    state = AppState.get(from_obj=request)
    file_path = os.path.join(state.get_audio_directory(), f"{unique_id}.pcm")
    file_mode = "ab" if os.path.exists(file_path) else "wb"

    try:
        with open(file_path, file_mode) as file:
            async for chunk in request.stream():
                file.write(chunk)
                file.flush()
    except ClientDisconnect:
        print(f"Client disconnected while streaming {unique_id}.")

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
    background_tasks.add_task(process_session_from_audio, state.transcription_service, state.llm_service, wave_file_name)

    return JSONResponse(content={"message": f"Audio processed"})
