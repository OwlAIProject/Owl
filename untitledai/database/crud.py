from sqlmodel import SQLModel, Session, select
from ..models.schemas import Transcription, Conversation, Utterance, Location
from typing import List, Optional
from sqlalchemy.orm import joinedload
from sqlalchemy import desc, func
from datetime import datetime


def create_transcription(db: Session, transcription: Transcription) -> Transcription:
    db.add(transcription)
    db.commit()
    db.refresh(transcription)
    return transcription

def get_transcription(db: Session, transcription_id: int) -> Transcription:
    statement = select(Transcription).where(Transcription.id == transcription_id)
    return db.exec(statement).first()

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

def get_all_conversations(db: Session, offset: int = 0, limit: int = 10) -> List[Conversation]:
    return db.query(Conversation).options(
        joinedload(Conversation.transcriptions).joinedload(Transcription.utterances).joinedload(Utterance.words)
    ).order_by(desc(Conversation.created_at)).offset(offset).limit(limit).all()

def create_location(db: Session, location_data: Location) -> Location:
    new_location = Location(latitude=location_data.latitude, longitude=location_data.longitude, address=location_data.address)
    db.add(new_location)
    db.commit()
    db.refresh(new_location)
    return new_location

def find_most_common_location(db: Session, start_time: datetime, end_time: datetime) -> Optional[Location]:
    most_common_location = (
        db.query(Location.id, Location.address, func.count(Location.id).label('address_count'))
          .filter(Location.created_at >= start_time, Location.created_at <= end_time)
          .group_by(Location.address)
          .order_by(desc('address_count'))
          .first()
    )
    if most_common_location:
        return db.get(Location, most_common_location.id)
    else:
        return None