from .streaming_deepgram_transcription_service import StreamingDeepgramTranscriptionService
from .streaming_whisper_transcription_service import StreamingWhisperTranscriptionService

import logging

logger = logging.getLogger(__name__)

class StreamingTranscriptionServiceFactory:
    _instances = {}

    @staticmethod
    def get_service(config, stream_format=None):
        service_type = config.streaming_transcription.provider

        if service_type not in StreamingTranscriptionServiceFactory._instances:
            logger.info(f"Creating new {service_type} streaming transcription service")
            if service_type == "deepgram":
                # Always make a new deepgram service
                return StreamingDeepgramTranscriptionService(config.deepgram, stream_format=stream_format)
            elif service_type == "whisper":
                StreamingTranscriptionServiceFactory._instances[service_type] = StreamingWhisperTranscriptionService(config.streaming_whisper, stream_format=stream_format)
                return StreamingTranscriptionServiceFactory._instances[service_type]
            else:
                raise ValueError(f"Unknown transcription service type: {service_type}")

        return StreamingTranscriptionServiceFactory._instances[service_type]
