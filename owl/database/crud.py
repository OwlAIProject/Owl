from sqlmodel import SQLModel, Session, select
from ..models.schemas import Transcription, Conversation, Utterance, Location, CaptureSegment, Capture, ConversationState, Image
from typing import List, Optional
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import desc, func, or_
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def create_image(db: Session, image: Image) -> Image:
    db.add(image)
    db.commit()
    db.refresh(image)
    return image

def create_utterance(db: Session, utterance: Utterance) -> Utterance:
    db.add(utterance)
    db.commit()
    db.refresh(utterance)
    return utterance

def create_transcription(db: Session, transcription: Transcription) -> Transcription:
    db.add(transcription)
    db.commit()
    db.refresh(transcription)
    return transcription

def create_capture_file_segment_file_ref(db: Session, capture_file_segment_file: CaptureSegment) -> CaptureSegment:
    db.add(capture_file_segment_file)
    db.commit()
    db.refresh(capture_file_segment_file)
    return capture_file_segment_file

def create_capture_file_ref(db: Session, capture_file_ref: Capture) -> Capture:
    db.add(capture_file_ref)
    db.commit()
    db.refresh(capture_file_ref)
    return capture_file_ref

def get_capture_file_ref(db: Session, capture_uuid: str) -> Optional[Capture]:
    statement = select(Capture).where(Capture.capture_uuid == capture_uuid)
    result = db.execute(statement).first()
    return result[0] if result else None

def get_capture_file_segment_file_ref(db: Session, conversation_uuid: str) -> Optional[CaptureSegment]:
    statement = select(CaptureSegment).where(CaptureSegment.conversation_uuid == conversation_uuid)
    result = db.execute(statement).first()
    return result[0] if result else None

def get_transcription(db: Session, transcription_id: int) -> Transcription:
    statement = select(Transcription).where(Transcription.id == transcription_id)
    return db.exec(statement).first()

def get_conversation(db: Session, conversation_id: int) -> Conversation:
    result = db.query(Conversation).options(
        selectinload(Conversation.transcriptions)
        .selectinload(Transcription.utterances)
        .selectinload(Utterance.words),
        selectinload(Conversation.capture_segment_file)
        .joinedload(CaptureSegment.source_capture),
        selectinload(Conversation.primary_location),
    ).filter(Conversation.id == conversation_id).first()
    return result

def get_conversation_by_conversation_uuid(db: Session, conversation_uuid: int) -> Conversation:
    return db.query(Conversation).options(
        joinedload(Conversation.capture_segment_file)
    ).options(
        joinedload(Conversation.transcriptions)
    ).options(
        joinedload(Conversation.primary_location)
    ).filter(Conversation.conversation_uuid == conversation_uuid).first()

def get_capturing_conversation_by_capture_uuid(db: Session, capture_uuid: str) -> Conversation:
    return db.query(Conversation).\
        options(
            joinedload(Conversation.capture_segment_file),
            joinedload(Conversation.transcriptions),
            joinedload(Conversation.primary_location)
        ).\
        join(CaptureSegment, CaptureSegment.id == Conversation.capture_segment_file_id).\
        join(Capture, Capture.id == CaptureSegment.source_capture_id).\
        filter(
            Capture.capture_uuid == capture_uuid,
            Conversation.state == ConversationState.CAPTURING
        ).\
        first()

def get_latest_capturing_conversation_by_capture_uuid(db: Session, capture_uuid: str) -> Optional[Conversation]:
    statement = (
        select(Conversation)
        .join(CaptureSegment, Conversation.capture_segment_file)
        .join(Capture, CaptureSegment.source_capture)   
        .where(Capture.capture_uuid == capture_uuid, Conversation.state == ConversationState.CAPTURING)
        .order_by(Conversation.start_time.desc())
        .limit(1)
    )
    result = db.execute(statement).scalars().first()
    return result

def update_latest_conversation_location(db: Session, capture_uuid: str, location_data: Location) -> Optional[Conversation]:
    latest_conversation = get_latest_capturing_conversation_by_capture_uuid(db, capture_uuid)
    
    if not latest_conversation:
        logger.error(f"No capturing conversation found for capture_uuid: {capture_uuid}")
        return None
    new_location = create_location(db, location_data)
    latest_conversation.primary_location_id = new_location.id
    db.commit()
    db.refresh(latest_conversation)
    
    return latest_conversation
def update_conversation_state(db: Session, conversation_id: int, new_state: ConversationState) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation:
        conversation.state = new_state
        db.commit()
        db.refresh(conversation)
        return conversation
    else:
        raise Exception(f"Conversation with ID {conversation_id} not found.")
    
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