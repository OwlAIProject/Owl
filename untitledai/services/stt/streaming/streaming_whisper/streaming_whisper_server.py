import asyncio
import websockets
import threading
import numpy as np
from scipy.signal import resample
import json
from .audio_to_text_recorder import AudioToTextRecorder
from multiprocessing import Process
from .....core.config import StreamingWhisperConfiguration
import logging

logger = logging.getLogger(__name__)

class StreamingWhisperServer:
    def __init__(self, config):
        self._config = config
        self._recorder = None
        self._recorder_ready = threading.Event()
        self._client_websocket = None

    async def _send_to_client(self, message):
        if self._client_websocket:
            await self._client_websocket.send(message)

    def _text_detected(self, text):
        asyncio.new_event_loop().run_until_complete(
            self._send_to_client(
                json.dumps({
                    'type': 'realtime',
                    'text': text
                })
            )
        )
        logger.info(f"\r{text}", flush=True, end='')

    def _recorder_thread(self):
        logger.info("Initializing RealtimeSTT...")
        recorder_config = {
            'spinner': False,
            'use_microphone': False,
            'model': self._config.model,
            'language': self._config.language,
            'silero_sensitivity': self._config.silero_sensitivity,
            'webrtc_sensitivity': self._config.webrtc_sensitivity,
            'post_speech_silence_duration': self._config.post_speech_silence_duration,
            'min_length_of_recording': 0,
            'min_gap_between_recordings': 0,
            'enable_realtime_transcription': True,
            'realtime_processing_pause': 0,
            'realtime_model_type': 'tiny.en',
            'on_realtime_transcription_stabilized': self._text_detected,
        }
        self._recorder = AudioToTextRecorder(**recorder_config)
        logger.info("RealtimeSTT initialized")
        self._recorder_ready.set()
        while True:
            full_sentence = self._recorder.text()
            asyncio.new_event_loop().run_until_complete(
                self._send_to_client(
                    json.dumps({
                        'type': 'fullSentence',
                        'text': full_sentence
                    })
                )
            )

    def _decode_and_resample(self, audio_data, original_sample_rate, target_sample_rate):
        audio_np = np.frombuffer(audio_data, dtype=np.int16)
        num_original_samples = len(audio_np)
        num_target_samples = int(num_original_samples * target_sample_rate / original_sample_rate)
        resampled_audio = resample(audio_np, num_target_samples)
        return resampled_audio.astype(np.int16).tobytes()

    async def echo(self, websocket, path):
        logger.info("Client connected")
        self._client_websocket = websocket
        async for message in websocket:
            if not self._recorder_ready.is_set():
                logger.info("Recorder not ready")
                continue

            metadata_length = int.from_bytes(message[:4], byteorder='little')
            metadata_json = message[4:4+metadata_length].decode('utf-8')
            metadata = json.loads(metadata_json)
            sample_rate = metadata['sampleRate']
            chunk = message[4+metadata_length:]
            resampled_chunk = self._decode_and_resample(chunk, sample_rate, 16000)
            self._recorder.feed_audio(resampled_chunk)

    def start(self):
        threading.Thread(target=self._recorder_thread).start()
        self._recorder_ready.wait()
        start_server = websockets.serve(self.echo, "localhost", 8009)
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()


def start_streaming_whisper_server_process(config):
    server = StreamingWhisperServer(config=config)  
    server.start()

def start_streaming_whisper_server(config: StreamingWhisperConfiguration):
    process = Process(target=start_streaming_whisper_server_process, args=(config,))
    process.start()
    return process
