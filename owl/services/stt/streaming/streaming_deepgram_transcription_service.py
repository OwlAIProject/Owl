from .abstract_streaming_transcription_service import AbstractStreamingTranscriptionService
from ....models.schemas import Word, Utterance
import asyncio
import websockets
from datetime import datetime, timedelta, timezone
import json
import logging

logger = logging.getLogger(__name__)
class StreamingDeepgramTranscriptionService(AbstractStreamingTranscriptionService):
    def __init__(self, config, stream_format=None):
        self.config = config
        self.websocket_url = "wss://api.deepgram.com/v1/listen"
        self.websocket = None
        self.on_utterance_callback = None
        self.stream_format = stream_format
        self.connection_lock = asyncio.Lock()
        self.is_receiving = False
        self.connection_open_time = None 

    def set_callback(self, callback):
        self.on_utterance_callback = callback

    def set_stream_format(self, stream_format):
        self._stream_format = stream_format

    async def _ensure_connection(self):
        async with self.connection_lock:
            if not self.websocket or self.websocket.closed:
                logger.info("Establishing new connection to Deepgram...")
                await self.start_transcription()

    async def start_transcription(self):
        try:
            headers = {"Authorization": f"Token {self.config.api_key}"}
            query_params = f"model={self.config.model}&language={self.config.language}&diarize=true"
            if self.stream_format:
                query_params += f"&sample_rate={self.stream_format['sample_rate']}&encoding={self.stream_format['encoding']}"
            self.websocket = await websockets.connect(f"{self.websocket_url}?{query_params}", extra_headers=headers)
            self.connection_open_time = datetime.now(timezone.utc)
            logger.info("Connected to Deepgram.")
            if not self.is_receiving:
                self.is_receiving = True
                asyncio.create_task(self.receive_transcriptions())
        except Exception as e:
            self.websocket = None
            logger.error(f"Failed to connect to Deepgram: {e}")
            await asyncio.sleep(1)  # Delay before retrying
            await self._ensure_connection()  # Attempt reconnection

    async def receive_transcriptions(self):
        try:
            while self.is_receiving:
                message = await self.websocket.recv()
                data = json.loads(message)
                if data['type'] == 'Results':
                    start = data['start']
                    end = start + data['duration']
                    transcript = data['channel']['alternatives'][0]['transcript']
                    words_data = data['channel']['alternatives'][0]['words']
                    
                    if not transcript.strip():
                        continue
                    
                    speaker = words_data[0].get('speaker') if words_data else None

                    words = [Word(word=w['word'], start=w['start'], end=w['end'], confidence=w['confidence'], speaker=w.get('speaker')) for w in words_data]
                    spoken_at = self.connection_open_time + timedelta(seconds=start)

                    utterance = Utterance(start=start, end=end, spoken_at=spoken_at, text=transcript, speaker=speaker, words=words, realtime=True)
                    
                    if self.on_utterance_callback:
                        await self.on_utterance_callback(utterance)

        except websockets.exceptions.ConnectionClosed:
            logger.info("Deepgram WebSocket connection closed.")
            self.is_receiving = False
        except Exception as e:
            self.is_receiving = False
            logger.error(f"Error receiving transcription: {e}")

    async def stop_transcription(self):
        if self.websocket:
            await self.websocket.send(json.dumps({"type": "CloseStream"}))
            await self.websocket.close()
            self.websocket = None
            self.is_receiving = False
            logger.info("Deepgram transcription stopped.")

    async def send_audio(self, audio_chunk):
        await self._ensure_connection()
        if self.websocket:
            try:
                await self.websocket.send(audio_chunk)
            except Exception as e:
                logger.error(f"Error sending audio to Deepgram: {e}")
                self.is_receiving = False
                await self.websocket.close()
                self.websocket = None
                await self._ensure_connection()
