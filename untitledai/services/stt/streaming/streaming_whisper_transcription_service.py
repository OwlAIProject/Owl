import asyncio
import websockets
import json
from numpy import int16, frombuffer, int32
from datetime import datetime, timedelta
import logging

from ....models.schemas import Utterance
from ....files.realtime_audio_converter import RealtimeAudioConverter
from .abstract_streaming_transcription_service import AbstractStreamingTranscriptionService

logger = logging.getLogger(__name__)

class StreamingWhisperTranscriptionService(AbstractStreamingTranscriptionService):
    def __init__(self, config, callback):
        self._callback = callback
        ffmpeg_command = [
            'ffmpeg', '-i', 'pipe:0', '-f', 's16le', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', 'pipe:1'
        ]
        self._converter = RealtimeAudioConverter(ffmpeg_command)
        self._converter_started = False
        self._websocket = None
        self._last_audio_time = None 
        self._retry_interval = 3  

    async def on_utterance(self, callback):
        self._callback = callback

    async def connect_to_websocket(self):
        while True:
            try:
                self._websocket = await websockets.connect("ws://localhost:8009")
                asyncio.create_task(self.listen_for_messages())
                logger.info("WebSocket connection established.")
                break
            except (OSError, websockets.exceptions.InvalidURI, websockets.exceptions.WebSocketException) as e:
                logger.error(f"Failed to connect to WebSocket, retrying in {self._retry_interval} seconds... Error: {e}")
                await asyncio.sleep(self._retry_interval)

    async def start_converter_and_process_audio(self):
        if not self._converter_started:
            self._converter_started = True
            await self._converter.start()
            logger.info("Converter started.")
            await self.connect_to_websocket()
            asyncio.create_task(self.receive_and_process_audio())

    async def send_audio(self, audio_chunk):
        self._last_audio_time = datetime.utcnow()  # Update last audio receive time
        await self.start_converter_and_process_audio()
        await self._converter.feed_input_chunk(audio_chunk)

    async def receive_and_process_audio(self):
        while True:
            output_chunk = await self._converter.read_output_chunk()
            if output_chunk:
                audio_chunk = frombuffer(output_chunk, dtype=int16)
                await self.send_audio_via_websocket(audio_chunk)
            else:
                logger.info("No more output from converter.")
                break
            await self.check_audio_timeout()

    async def listen_for_messages(self):
        try:
            while True:
                message = await self._websocket.recv()
                if not message:
                    continue
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode JSON from message: {message}")
                    continue
                logger.info(f"Received message: {data}")
                if data.get('type') == 'fullSentence' and data.get('text'):
                    if self._callback:
                        utterance = Utterance(spoken_at=datetime.utcnow(), text=data['text'], realtime=True)
                        await self._callback(utterance)
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed.")
        except Exception as e:
            logger.error(f"An unexpected error occurred while listening for messages: {e}")

    async def send_audio_via_websocket(self, audio_chunk):
        if self._websocket and self._websocket.open:
            audio_data_bytes = audio_chunk.tobytes()
            metadata = {"sampleRate": 16000}
            metadata_json = json.dumps(metadata)
            metadata_bytes = metadata_json.encode('utf-8')
            metadata_size = int32(len(metadata_bytes)).tobytes()
            message = metadata_size + metadata_bytes + audio_data_bytes
            await self._websocket.send(message)
        else:
            logger.info("WebSocket connection is not open.")

    async def check_audio_timeout(self):
        if self._last_audio_time and datetime.utcnow() - self._last_audio_time > timedelta(seconds=10):
            await self.close_websocket()
            logger.info("WebSocket closed due to inactivity.")

    async def close_websocket(self):
        if self._websocket:
            await self._websocket.close()
            self._websocket = None  
            logger.info("WebSocket connection closed.")
