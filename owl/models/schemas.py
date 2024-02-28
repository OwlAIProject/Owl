from typing import List, Optional
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from pydantic import BaseModel
from enum import Enum

from .datetime_serialization import datetime_string


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
    spoken_at: Optional[datetime] = None
    realtime: bool = Field(default=False)
    text: Optional[str] = None
    speaker: Optional[str] = None
    transcription_id: Optional[int] = Field(default=None, foreign_key="transcription.id")

    transcription: "Transcription" = Relationship(back_populates="utterances")

    words: List[Word] = Relationship(back_populates="utterance", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class Transcription(CreatedAtMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    realtime: bool = Field(default=False)
    model: str
    transcription_time: float
    conversation_id: Optional[int] = Field(default=None, foreign_key="conversation.id")
    conversation: "Conversation" = Relationship(back_populates="transcriptions")
    utterances: List[Utterance] = Relationship(back_populates="transcription", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class Location(CreatedAtMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    latitude: float = Field(nullable=False)
    longitude: float = Field(nullable=False)
    address: Optional[str] = None
    capture_uuid: Optional[str] = None

    conversation: Optional["Conversation"] = Relationship(back_populates="primary_location")

class ConversationState(Enum):
    CAPTURING = "CAPTURING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED_PROCESSING = "FAILED_PROCESSING"

class Conversation(CreatedAtMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    start_time: datetime = Field(...)
    end_time: Optional[datetime]
    conversation_uuid: str
    device_type: str
    summary: Optional[str]
    short_summary: Optional[str]
    summarization_model: Optional[str]
    state: ConversationState = Field(default=ConversationState.CAPTURING)

    capture_segment_file_id: Optional[int] = Field(default=None, foreign_key="capturesegment.id")
    capture_segment_file: Optional["CaptureSegment"] = Relationship(back_populates="conversation")
    transcriptions: List[Transcription] = Relationship(back_populates="conversation")
    primary_location_id: Optional[int] = Field(default=None, foreign_key="location.id")
    primary_location: Optional[Location] = Relationship(back_populates="conversation")
    suggested_links: List["SuggestedLink"] = Relationship(back_populates="conversation")
    images: List["Image"] = Relationship(back_populates="conversation")

class SuggestedLink(CreatedAtMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: Optional[int] = Field(default=None, foreign_key="conversation.id")
    url: str 
    conversation: Optional['Conversation'] = Relationship(back_populates="suggested_links")

class Capture(CreatedAtMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    capture_uuid: str
    filepath: str = Field(...)
    start_time: datetime
    device_type: str
    duration: Optional[float]

    capture_segment_files: List["CaptureSegment"] = Relationship(back_populates="source_capture")
    images: List["Image"] = Relationship(back_populates="source_capture")

class CaptureSegment(CreatedAtMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filepath: str = Field(...)
    start_time: datetime
    conversation_uuid: str
    source_capture_id: int = Field(default=None, foreign_key="capture.id")
    source_capture: Capture = Relationship(back_populates="capture_segment_files")
    duration: Optional[float]

    conversation: Optional[Conversation] = Relationship(back_populates="capture_segment_file")

class Image(CreatedAtMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filepath: str = Field(...)
    captured_at: datetime
    conversation_uuid: str
    source_capture_id: int = Field(default=None, foreign_key="capture.id")
    source_capture: Capture = Relationship(back_populates="images")
    conversation_id: Optional[int] = Field(default=None, foreign_key="conversation.id")
    conversation: Optional["Conversation"] = Relationship(back_populates="images")

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
    spoken_at: Optional[datetime]
    text: Optional[str]
    speaker: Optional[str]
    class Config:
        from_attributes=True
        json_encoders = {
            datetime: datetime_string
        }

class CaptureRead(BaseModel):
    id: Optional[int]
    capture_uuid: str
    filepath: str
    start_time: datetime
    duration: Optional[float]
    device_type: str
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: datetime_string
        }

class CaptureSegmentRead(BaseModel):
    id: Optional[int]
    filepath: str
    duration: Optional[float]
    start_time: datetime
    source_capture: Optional[CaptureRead] = None
    source_capture_id: Optional[int] = None
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: datetime_string
        }

class TranscriptionRead(BaseModel):
    id: Optional[int] = None
    realtime: Optional[bool] = None
    model: Optional[str] = None
    transcription_time: Optional[float] = None
    conversation_id: Optional[int] = None
    utterances: List[UtteranceRead] = []
    class Config:
        from_attributes = True

class LocationRead(BaseModel):
    id: Optional[int]
    latitude: float
    longitude: float
    address: Optional[str]
    class Config:
        from_attributes=True

class ConversationRead(BaseModel):
    id: Optional[int]
    state: ConversationState
    start_time: datetime
    conversation_uuid: str
    device_type: str
    summarization_model: Optional[str]
    summary: Optional[str]
    short_summary: Optional[str]
    transcriptions: List[TranscriptionRead] = []
    suggested_links: List[SuggestedLink] = []
    primary_location: Optional[LocationRead] = None
    capture_segment_file: Optional[CaptureSegmentRead]

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: datetime_string
        }

class ConversationsResponse(BaseModel):
    conversations: List[ConversationRead]
