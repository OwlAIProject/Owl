from typing import List, Optional
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone

class CreatedAtMixin(SQLModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)

class Word(CreatedAtMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    word: str
    start: Optional[float] = None
    end: Optional[float] = None
    score: Optional[float] = None
    speaker: Optional[str] = None
    utterance_id: Optional[int] = Field(default=None, foreign_key="utterance.id")
    
    utterance: "Utterance" = Relationship(back_populates="words")

    
class Utterance(CreatedAtMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    start: Optional[float] = None
    end: Optional[float] = None
    text: Optional[str] = None
    speaker: Optional[str] = None
    transcription_id: Optional[int] = Field(default=None, foreign_key="transcription.id")
    
    transcription: "Transcription" = Relationship(back_populates="utterances")
  
    words: List[Word] = Relationship(back_populates="utterance", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class Transcription(CreatedAtMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    model: str 
    file_name: str 
    duration: float  
    source_device: str 
    transcription_time: float 
    conversation_id: Optional[int] = Field(default=None, foreign_key="conversation.id")

    conversation: "Conversation" = Relationship(back_populates="transcriptions")

    utterances: List[Utterance] = Relationship(back_populates="transcription", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class Conversation(CreatedAtMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    summary: str  
    transcriptions: List[Transcription] = Relationship(back_populates="conversation")
