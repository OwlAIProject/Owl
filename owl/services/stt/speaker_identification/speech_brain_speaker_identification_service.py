
from .abstract_speaker_identification_service import AbstractSpeakerIdentificationService
from ....models.schemas import Transcription, Person
from typing import List
import logging

logger = logging.getLogger(__name__)

class SpeechBrainIdentificationService(AbstractSpeakerIdentificationService):
    def __init__(self, config):
        self._config = config

    async def identify_speakers(self, transcript: Transcription, persons: List[Person]) -> Transcription:
        # stub implementation. just set the first person in the list as the speaker for all utterances
        for utterance in transcript.utterances:
            utterance.person = persons[0]
        return transcript