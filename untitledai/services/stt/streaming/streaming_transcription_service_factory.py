from .streaming_deepgram_transcription_service import StreamingDeepgramTranscriptionService
import logging

logger = logging.getLogger(__name__)

class StreamingTranscriptionServiceFactory:
    _instances = {}

    @staticmethod
    def get_service(config, callback):
        service_type = config.streaming_transcription.provider

        if service_type not in StreamingTranscriptionServiceFactory._instances:
            logger.info(f"Creating new {service_type} streaming transcription service")
            if service_type == "deepgram":
                StreamingTranscriptionServiceFactory._instances[service_type] = StreamingDeepgramTranscriptionService(config.deepgram, callback)
            else:
                raise ValueError(f"Unknown transcription service type: {service_type}")

        return StreamingTranscriptionServiceFactory._instances[service_type]
