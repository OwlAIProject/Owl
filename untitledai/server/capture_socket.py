import os
import socketio
import asyncio
from datetime import datetime
from ..core.config import CaptureConfig
from ..services.session.session_service import process_session_from_audio

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

socket_app = socketio.ASGIApp(sio)

current_file = None
current_file_name = ""
last_audio_time = None
file_timeout_task = None

audio_directory = f"{CaptureConfig.CAPTURE_DIRECTORY}/audio"

async def file_timeout():
    global current_file, last_audio_time
    while current_file and (asyncio.get_event_loop().time() - last_audio_time) <= 10:
        await asyncio.sleep(1)
    if current_file:
        print(f"File {current_file_name} closed due to timeout.")
        await close_and_process_file()

async def close_and_process_file():
    global current_file, current_file_name
    if current_file:
        current_file.close()
        current_file = None
        print(f"File {current_file_name} closed.")

        try:
            await process_session_from_audio(current_file_name)
        except Exception as e:
            print(f"Error processing session from audio: {e}")

# Socket.IO Events
@sio.event
async def connect(sid, environ):
    print('Connected: ', sid)

@sio.event
async def disconnect(sid):
    print('Disconnected: ', sid)

@sio.event
async def audio_data(sid, binary_data):
    print(sid)
    global current_file, current_file_name, last_audio_time, file_timeout_task
    if not current_file:
        current_file_name = os.path.join(audio_directory, f"audio_{datetime.now().strftime('%Y%m%d%H%M%S')}.aac")
        current_file = open(current_file_name, "ab")
        last_audio_time = asyncio.get_event_loop().time()
        if file_timeout_task:
            file_timeout_task.cancel()
        file_timeout_task = asyncio.create_task(file_timeout())
    current_file.write(binary_data)
    last_audio_time = asyncio.get_event_loop().time()

@sio.event
async def finish_audio(sid):
    await close_and_process_file()