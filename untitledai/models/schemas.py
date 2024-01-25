from typing import List, Optional
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from pydantic import BaseModel, validator

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

class Location(CreatedAtMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    latitude: float = Field(nullable=False)
    longitude: float = Field(nullable=False)
    address: Optional[str] = None

    # Relationship with Conversation
    conversation: Optional["Conversation"] = Relationship(back_populates="primary_location")


class Conversation(CreatedAtMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    start_time: datetime = Field(...)
    summary: str  
    transcriptions: List[Transcription] = Relationship(back_populates="conversation")

    primary_location_id: Optional[int] = Field(default=None, foreign_key="location.id")
    primary_location: Optional[Location] = Relationship(back_populates="conversation")

#  API Response Models
#  https://sqlmodel.tiangolo.com/tutorial/fastapi/relationships/#dont-include-all-the-data
    
class WordRead(BaseModel):
    id: Optional[int]
    word: str
    start: Optional[float]
    end: Optional[float]
    score: Optional[float]
    speaker: Optional[str]
    utterance_id: Optional[int]
    class Config:
        from_attributes=True


class UtteranceRead(BaseModel):
    id: Optional[int]
    start: Optional[float]
    end: Optional[float]
    text: Optional[str]
    speaker: Optional[str]
    words: List[WordRead] = []
    class Config:
        from_attributes=True

class TranscriptionRead(BaseModel):
    id: Optional[int]
    model: str 
    file_name: str 
    duration: float  
    source_device: str 
    transcription_time: float
    utterances: List[UtteranceRead] = []
    class Config:
        from_attributes=True

class LocationRead(BaseModel):
    id: Optional[int]
    latitude: float
    longitude: float
    address: Optional[str]
    class Config:
        from_attributes=True

class ConversationRead(BaseModel):
    id: Optional[int]
    start_time: datetime
    summary: str  
    transcriptions: List[TranscriptionRead] = []
    primary_location: Optional[LocationRead] = None

    class Config:
        from_attributes = True

class ConversationsResponse(BaseModel):
    conversations: List[ConversationRead]