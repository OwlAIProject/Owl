from abc import ABC, abstractmethod
from ....models.schemas import Transcription

class AbstractAsyncTranscriptionService(ABC):
    
    @abstractmethod
    async def transcribe_audio(self, main_audio_filepath, voice_sample_filepath=None, speaker_name=None) -> Transcription:
        pass

