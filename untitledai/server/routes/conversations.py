
from fastapi import APIRouter, Depends, Query, Request
from sqlmodel import Session

from ...server.app_state import AppState
from ...models.schemas import ConversationsResponse 
from ...database.crud import get_all_conversations
from typing import List

router = APIRouter()

@router.get("/conversations/", response_model=ConversationsResponse)
def read_conversations(
    offset: int = 0, 
    limit: int = Query(default=100), 
    db: Session = Depends(AppState.get_db)
):
    conversations = get_all_conversations(db, offset, limit)
    return ConversationsResponse(conversations=conversations)