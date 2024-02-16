import logging

from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlmodel import Session

from fastapi.encoders import jsonable_encoder
from ...server.app_state import AppState
from ...models.schemas import ConversationsResponse, ConversationRead, CaptureSegmentRead
from ...database.crud import get_all_conversations, get_conversation, delete_conversation
from ...devices import DeviceType
from typing import List
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()

def process_conversation_background_task(conversation_uuid: str, app_state: AppState):
    asyncio.run(app_state.conversation_service.process_conversation_from_audio(conversation_uuid=conversation_uuid))

@router.post("/conversations/{conversation_id}/retry", response_model=ConversationRead)
def read_conversation(
    conversation_id: int, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(AppState.get_db),
    app_state: AppState = Depends(AppState.authenticate_request)
):
    conversation = get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    background_tasks.add_task(process_conversation_background_task, conversation.conversation_uuid, app_state)


    return conversation

@router.post("/conversations/{conversation_id}/end", response_model=ConversationRead)
async def end_conversation(
    conversation_id: int, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(AppState.get_db),
    app_state: AppState = Depends(AppState.authenticate_request)
):
    conversation = get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    capture_uuid = conversation.capture_segment_file.source_capture.capture_uuid
    if capture_uuid not in app_state.capture_handlers:
        logger.error(f"Capture session not found: {capture_uuid}")
        raise HTTPException(status_code=500, detail="Capture session not found")
    capture_handler = app_state.capture_handlers[capture_uuid]

    await capture_handler.on_endpoint()
    return conversation

@router.get("/conversations/{conversation_id}", response_model=ConversationRead)
def read_conversation(
    conversation_id: int, 
    db: Session = Depends(AppState.get_db),
    app_state: AppState = Depends(AppState.authenticate_request)
):
    conversation = get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation

@router.get("/conversations/", response_model=ConversationsResponse)
def read_conversations(
    offset: int = 0, 
    limit: int = Query(default=100), 
    db: Session = Depends(AppState.get_db),
    app_state: AppState = Depends(AppState.authenticate_request)
):
    conversations = get_all_conversations(db, offset, limit)

    return ConversationsResponse(conversations=conversations)

@router.delete("/conversations/{conversation_id}")
def delete_conversation_endpoint(
    conversation_id: int, 
    db: Session = Depends(AppState.get_db),
    app_state: AppState = Depends(AppState.authenticate_request)
):
    success = delete_conversation(db, conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return JSONResponse(content={"success": True}, status_code=200)