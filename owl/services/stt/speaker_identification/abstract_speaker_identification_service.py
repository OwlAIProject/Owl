from abc import ABC, abstractmethod
from ....models.schemas import Transcription, Conversation, Person
from typing import List

class AbstractSpeakerIdentificationService(ABC):
    
    @abstractmethod
    async def identify_speakers(self, transcript: Transcription, conversation: Conversation, persons: List[Person]) -> Transcription:
        pass