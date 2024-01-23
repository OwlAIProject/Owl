
from fastapi import APIRouter, Depends, Query, Request
from sqlmodel import Session

from ...server.app_state import AppState
from ...models.schemas import Conversation, ConversationRead, ConversationsResponse 
from ...database.crud import get_all_conversations
from typing import List

router = APIRouter()

def get_database(request: Request):
    app_state: AppState = AppState.get(request)
    return app_state.database.get_db()

@router.get("/conversations/", response_model=ConversationsResponse)
def read_conversations(
    offset: int = 0, 
    limit: int = Query(default=100), 
    database: Session = Depends(get_database)
):
    with next(database) as db:
        conversations = get_all_conversations(db, offset, limit)

    return ConversationsResponse(conversations=conversations)
