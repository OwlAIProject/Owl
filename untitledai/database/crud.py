from sqlmodel import SQLModel, Session, select
from ..models.schemas import Transcription, Conversation, Utterance, Location, SegmentedCaptureFile, CaptureFileRef
from typing import List, Optional
from sqlalchemy.orm import joinedload
from sqlalchemy import desc, func, or_
from datetime import datetime


def create_transcription(db: Session, transcription: Transcription) -> Transcription:
    db.add(transcription)
    db.commit()
    db.refresh(transcription)
    return transcription

def create_segmented_capture_file(db: Session, segmented_capture_file: SegmentedCaptureFile) -> SegmentedCaptureFile:
    db.add(segmented_capture_file)
    db.commit()
    db.refresh(segmented_capture_file)
    return segmented_capture_file

def create_capture_file_ref(db: Session, capture_file_ref: CaptureFileRef) -> CaptureFileRef:
    db.add(capture_file_ref)
    db.commit()
    db.refresh(capture_file_ref)
    return capture_file_ref

def get_capture_file_ref(db: Session, capture_uuid: str) -> Optional[CaptureFileRef]:
    statement = select(CaptureFileRef).where(CaptureFileRef.capture_uuid == capture_uuid)
    result = db.execute(statement).first()
    return result[0] if result else None

def get_transcription(db: Session, transcription_id: int) -> Transcription:
    statement = select(Transcription).where(Transcription.id == transcription_id)
    return db.exec(statement).first()

def get_conversation(db: Session, conversation_id: int) -> Conversation:
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()

def update_transcription(db: Session, transcription_id: int, updated_transcription: Transcription) -> Transcription:
    db_transcription = db.get(Transcription, transcription_id)
    if db_transcription:
        db_transcription.text = updated_transcription.text 
        db.commit()
        db.refresh(db_transcription)
    return db_transcription

def delete_transcription(db: Session, transcription_id: int):
    db_transcription = db.get(Transcription, transcription_id)
    if db_transcription:
        db.delete(db_transcription)
        db.commit()

def create_conversation(db: Session, conversation: Conversation) -> Conversation:
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

def delete_conversation(db: Session, conversation_id: int) -> bool:
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        return False

    db.delete(conversation)
    db.commit()
    return True

def get_all_conversations(db: Session, offset: int = 0, limit: int = 10) -> List[Conversation]:
    return db.query(Conversation).options(
        joinedload(Conversation.transcriptions).joinedload(Transcription.utterances).joinedload(Utterance.words)
    ).order_by(desc(Conversation.created_at)).offset(offset).limit(limit).all()

def create_location(db: Session, location_data: Location) -> Location:
    new_location = Location(latitude=location_data.latitude, longitude=location_data.longitude, address=location_data.address, capture_uuid=location_data.capture_uuid)
    db.add(new_location)
    db.commit()
    db.refresh(new_location)
    return new_location

def find_most_common_location(db: Session, start_time: datetime, end_time: datetime, capture_uuid: Optional[str] = None) -> Optional[Location]:
    print(f"Finding most common location between {start_time} and {end_time} for capture {capture_uuid}")
    query = (
        db.query(Location.id, Location.address, func.count(Location.id).label('address_count'))
          .filter(or_(Location.created_at.between(start_time, end_time), 
                      Location.capture_uuid == capture_uuid))
          .group_by(Location.address)
          .order_by(desc('address_count'))
          .first()
    )

    if query:
        return db.get(Location, query.id)
    else:
        return None