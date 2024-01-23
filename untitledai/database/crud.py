from sqlmodel import SQLModel, Session, select
from ..models.schemas import Transcription, Conversation, Utterance
from typing import List

from sqlalchemy.orm import joinedload

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
    ).offset(offset).limit(limit).all()