from .abstract_streaming_transcription_service import AbstractStreamingTranscriptionService
import asyncio
import websockets
import json
import logging

class StreamingDeepgramTranscriptionService(AbstractStreamingTranscriptionService):

    def __init__(self, config, callback):
        self.config = config
        self.websocket_url = "wss://api.deepgram.com/v1/listen"
        self.websocket = None
        self.on_utterance_callback = callback
        self.connection_lock = asyncio.Lock()
        self.is_receiving = False

    async def _ensure_connection(self):
        async with self.connection_lock:
            if not self.websocket or self.websocket.closed:
                logging.info("Establishing new connection to Deepgram...")
                await self.start_transcription()

    async def start_transcription(self):
        try:
            headers = {"Authorization": f"Token {self.config.api_key}"}
            query_params = f"model={self.config.model}&language={self.config.language}"
            self.websocket = await websockets.connect(f"{self.websocket_url}?{query_params}", extra_headers=headers)
            logging.info("Connected to Deepgram.")
            if not self.is_receiving:
                self.is_receiving = True
                asyncio.create_task(self.receive_transcriptions())
        except Exception as e:
            self.websocket = None
            logging.error(f"Failed to connect to Deepgram: {e}")
            await asyncio.sleep(1)  # Delay before retrying, adjust as needed
            await self._ensure_connection()  # Attempt reconnection

    async def receive_transcriptions(self):
        try:
            while self.is_receiving:
                message = await self.websocket.recv()
                data = json.loads(message)
                if data['type'] == 'Results':
                    sentence = data['channel']['alternatives'][0]['transcript']
                    if sentence and self.on_utterance_callback:
                        await self.on_utterance_callback(sentence)
        except websockets.exceptions.ConnectionClosed:
            logging.info("Deepgram WebSocket connection closed. Attempting to reconnect...")
            self.is_receiving = False
            await self._ensure_connection()
        except Exception as e:
            self.is_receiving = False
            logging.error(f"Error receiving transcription: {e}")

    async def stop_transcription(self):
        if self.websocket:
            await self.websocket.send(json.dumps({"type": "CloseStream"}))
            await self.websocket.close()
            self.websocket = None
            self.is_receiving = False
            logging.info("Deepgram transcription stopped.")

    async def send_audio(self, audio_chunk):
        await self._ensure_connection()
        if self.websocket:
            try:
                await self.websocket.send(audio_chunk)
            except Exception as e:
                logging.error(f"Error sending audio to Deepgram: {e}")
                await self.websocket.close()
                self.websocket = None
                self.is_receiving = False
                await self._ensure_connection()

    async def on_utterance(self, callback):
        self.on_utterance_callback = callback
