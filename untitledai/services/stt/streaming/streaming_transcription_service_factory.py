from .streaming_deepgram_transcription_service import StreamingDeepgramTranscriptionService

class StreamingTranscriptionServiceFactory:
    _instances = {}

    @staticmethod
    def get_service(config, callback):
        service_type = config.streaming_transcription.provider
        if service_type not in StreamingTranscriptionServiceFactory._instances:
            if service_type == "deepgram":
                print("Creating new Deepgram service")
                StreamingTranscriptionServiceFactory._instances[service_type] = StreamingDeepgramTranscriptionService(config.deepgram, callback)
            else:
                raise ValueError(f"Unknown transcription service type: {service_type}")

        return StreamingTranscriptionServiceFactory._instances[service_type]
