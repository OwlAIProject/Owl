from typing import List, Optional
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from pydantic import BaseModel, validator
from enum import Enum

from .datetime_serialization import timestamp_string


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

    capture_segment_file_id: Optional[int] = Field(default=None, foreign_key="capturesegmentfileref.id")
    capture_segment_file: Optional["CaptureSegmentFileRef"] = Relationship(back_populates="conversation")
    transcriptions: List[Transcription] = Relationship(back_populates="conversation")
    primary_location_id: Optional[int] = Field(default=None, foreign_key="location.id")
    primary_location: Optional[Location] = Relationship(back_populates="conversation")

class CaptureFileRef(CreatedAtMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    capture_uuid: str
    file_path: str = Field(...)
    start_time: datetime
    device_type: str
    duration: Optional[float]

    capture_segment_files: List["CaptureSegmentFileRef"] = Relationship(back_populates="source_capture")

class CaptureSegmentFileRef(CreatedAtMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    file_path: str = Field(...)
    start_time: datetime
    conversation_uuid: str
    source_capture_id: int = Field(default=None, foreign_key="capturefileref.id")
    source_capture: CaptureFileRef = Relationship(back_populates="capture_segment_files")
    duration: Optional[float]

    conversation: Optional[Conversation] = Relationship(back_populates="capture_segment_file")

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
            datetime: timestamp_string
        }

class CaptureFileRefRead(BaseModel):
    id: Optional[int]
    capture_uuid: str
    file_path: str
    start_time: datetime
    duration: Optional[float]
    device_type: str
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: timestamp_string
        }

class CaptureSegmentFileRefRead(BaseModel):
    id: Optional[int]
    file_path: str
    duration: Optional[float]
    start_time: datetime
    source_capture: Optional[CaptureFileRefRead] = None
    source_capture_id: Optional[int] = None
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: timestamp_string
        }

class TranscriptionRead(BaseModel):
    id: Optional[int]
    realtime: bool
    model: str
    transcription_time: float
    conversation_id: Optional[int]
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
    primary_location: Optional[LocationRead] = None
    capture_segment_file: Optional[CaptureSegmentFileRefRead]

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: timestamp_string
        }

class ConversationsResponse(BaseModel):
    conversations: List[ConversationRead]
