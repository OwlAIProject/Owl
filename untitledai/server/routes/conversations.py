import logging

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session

from ...server.app_state import AppState
from ...models.schemas import ConversationsResponse, ConversationRead, ConversationInProgress
from ...database.crud import get_all_conversations, get_conversation, delete_conversation
from ...devices import DeviceType
from typing import List

logger = logging.getLogger(__name__)

router = APIRouter()

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
    conversations_in_progress = []
    for capture_uuid, detection_service in app_state.conversation_detection_service_by_id.items():
        current_conversation_start_time = detection_service.current_conversation_start_time()
        if current_conversation_start_time is not None:
            # Conversation in progress, look up its device from the capture file
            capture_file = app_state.capture_files_by_id.get(capture_uuid)
            if capture_file is not None:
                conversation_in_progress = ConversationInProgress(
                    capture_uuid=capture_uuid,
                    start_time=current_conversation_start_time,
                    device_type=capture_file.device_type.value
                )
                conversations_in_progress.append(conversation_in_progress)
            else:
                logger.error(f"Conversation in progress with capture_uuid={capture_uuid} but no capture file object")

    return ConversationsResponse(conversations=conversations, conversations_in_progress=conversations_in_progress)

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