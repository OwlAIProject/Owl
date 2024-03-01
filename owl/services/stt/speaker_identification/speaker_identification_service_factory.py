from .speech_brain_speaker_identification_service import SpeechBrainIdentificationService
import logging

logger = logging.getLogger(__name__)

class SpeakerIdentificationServiceFactory:
    _instances = {}

    @staticmethod
    def get_service(config):
        service_type = config.speaker_identification.provider
        if service_type not in SpeakerIdentificationServiceFactory._instances:
            logger.info(f"Creating new {service_type} speaker identification service")
            if service_type == "speech_brain":
                SpeakerIdentificationServiceFactory._instances[service_type] = SpeechBrainIdentificationService(config.speech_brain)
            else:
                raise ValueError(f"Unknown speaker identification service type: {service_type}")

        return SpeakerIdentificationServiceFactory._instances[service_type]

