from abc import ABC, abstractmethod
from ....models.schemas import Transcript

class AbstractSpeakerIdentificationService(ABC):
    
    @abstractmethod
    async def identifiy_speakers(self, transcript: Transcript, persons) -> Transcript:
        pass