from typing import List, Optional
from pydantic import BaseModel

class Word(BaseModel):
    word: str
    start: Optional[float]
    end: Optional[float]
    score: Optional[float]
    speaker: Optional[str]

class Utterance(BaseModel):
    start: Optional[float]
    end: Optional[float]
    text: Optional[str]
    words: List[Word]
    speaker: Optional[str]

class Transcription(BaseModel):
    utterances: List[Utterance]