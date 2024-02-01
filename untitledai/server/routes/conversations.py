
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session

from ...server.app_state import AppState
from ...models.schemas import ConversationsResponse 
from ...database.crud import get_all_conversations, delete_conversation
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

@router.delete("/conversations/{conversation_id}/")
def delete_conversation_endpoint(
    conversation_id: int, 
    db: Session = Depends(AppState.get_db)
):
    success = delete_conversation(db, conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return JSONResponse(content={"success": True}, status_code=200)