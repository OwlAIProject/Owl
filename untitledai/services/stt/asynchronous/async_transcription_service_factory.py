from .async_whisper_transcription_service import AsyncWhisperTranscriptionService
from .async_deepgram_transcription_service import AsyncDeepgramTranscriptionService

class AsyncTranscriptionServiceFactory:
    _instances = {}

    @staticmethod
    def get_service(config):
        service_type = config.async_transcription.provider
        if service_type not in AsyncTranscriptionServiceFactory._instances:
            print(f"Creating new {service_type} service")
            if service_type == "whisper":
                AsyncTranscriptionServiceFactory._instances[service_type] = AsyncWhisperTranscriptionService(config.transcription)
            elif service_type == "deepgram":
                AsyncTranscriptionServiceFactory._instances[service_type] = AsyncDeepgramTranscriptionService(config.deepgram)
            else:
                raise ValueError(f"Unknown transcription service type: {service_type}")

        return AsyncTranscriptionServiceFactory._instances[service_type]

