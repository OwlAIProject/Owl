import os
import asyncio
from datetime import datetime, timezone
from queue import Queue
import logging
from ..services.stt.streaming.streaming_transcription_service_factory import StreamingTranscriptionServiceFactory
from ..services.endpointing.streaming.streaming_endpointing_service import StreamingEndpointingService
from ..files import CaptureFile
from pydub import AudioSegment

logger = logging.getLogger(__name__)

class StreamingCaptureHandler:
    def __init__(self, app_state, device_name, capture_id, file_extension="aac", stream_format=None):
        self.app_state = app_state
        self.device_name = device_name
        self.capture_id = capture_id
        self.file_extension = file_extension
        self.segment_file = None
        self.segment_counter = 0
        self.transcription_service = StreamingTranscriptionServiceFactory.get_service(
            app_state.config, self.handle_utterance, stream_format=stream_format
        )
        
        self.endpointing_service = StreamingEndpointingService(
            timeout_interval=app_state.config.endpointing.timeout_interval,
            min_utterances=app_state.config.endpointing.min_utterances,
            endpoint_callback=lambda: asyncio.create_task(self.on_endpoint())
        )

        self._init_capture_session()

    def _init_capture_session(self):
        self.capture_file = CaptureFile(
            audio_directory=self.app_state.get_audio_directory(),
            capture_id=self.capture_id,
            device_type=self.device_name,
            timestamp=datetime.now(timezone.utc),
            file_extension=self.file_extension
        )
        self.temp_pcm_file = None 
        if self.file_extension == "wav":
            self.temp_pcm_file = os.path.splitext(self.capture_file.filepath)[0] + ".pcm"
        self.start_new_segment()

    async def on_endpoint(self):
        logger.info(f"Endpoint detected for capture_id {self.capture_id}")
        if self.capture_file and self.segment_file:
            self.process_conversation(self.capture_file, self.segment_file)
        self.start_new_segment()

    def process_conversation(self, capture_file, segment_file):
        if self.file_extension == "wav":
            self.convert_pcm_to_wav(segment_file)
        
        logger.info(f"Processing conversation for capture_id {capture_file.capture_id} ({segment_file})")

        task = (capture_file, segment_file)
        self.app_state.conversation_task_queue.put(task)
    async def handle_audio_data(self, binary_data):
        with open(self.temp_pcm_file if self.file_extension == "wav" else self.capture_file.filepath, "ab") as file:
            file.write(binary_data)

        if self.segment_file:
            with open(self.segment_file, "ab") as file:
                file.write(binary_data)

        await self.transcription_service.send_audio(binary_data)

    async def handle_utterance(self, utterance):
        logger.info(f"Received utterance: {utterance}")
        asyncio.create_task(self.endpointing_service.utterance_detected())

    def start_new_segment(self):
        segment_number = self.segment_counter + 1
        self.segment_counter = segment_number
        capture_file_dir = os.path.dirname(self.capture_file.filepath)
        base_name = os.path.splitext(os.path.basename(self.capture_file.filepath))[0]
        segment_file_name = f"{base_name}-{segment_number}.{self.file_extension}"
        segment_file_path = os.path.join(capture_file_dir, segment_file_name)
        self.segment_file = segment_file_path
        if self.file_extension == "wav":
            self.segment_file = f"{os.path.splitext(self.segment_file)[0]}.pcm"
        with open(segment_file_path, "wb") as file:
            pass  # Creating an empty segment file

    def finish_capture_session(self):
        if self.segment_file:
            self.process_conversation(self.capture_file, self.segment_file)
       
        capture_file = self.app_state.capture_sessions_by_id.pop(self.capture_id, None)
        if self.file_extension == "wav" and self.temp_pcm_file:
            self.convert_pcm_to_wav(self.temp_pcm_file)
        if self.endpointing_service:
            self.endpointing_service.stop()
        logger.info(f"Finishing capture: {self.capture_id}")
        if capture_file:
            try:
                with open(capture_file.filepath, "a"):
                    pass  # Finalize the capture file
            except Exception as e:
                logger.error(f"Error closing file {capture_file.filepath}: {e}")

    @staticmethod
    def convert_pcm_to_wav(pcm_file_path):
        wav_file_path = f"{os.path.splitext(pcm_file_path)[0]}.wav"
        audio = AudioSegment.from_file(pcm_file_path, format="raw", frame_rate=16000, channels=1, sample_width=2)
        audio.export(wav_file_path, format="wav")
        os.remove(pcm_file_path)