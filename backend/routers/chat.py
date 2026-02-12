"""Chat conversation persistence router."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_active_user
from database import get_db
from models import ChatConversation, User
from org_context import require_org
from schemas import (
    ChatConversationCreate,
    ChatConversationListItem,
    ChatConversationResponse,
    ChatConversationUpdate,
)

router = APIRouter()


def get_conversation_or_404(
    db: Session,
    convo_id: UUID,
    user_id: UUID,
    org_id: UUID,
) -> ChatConversation:
    convo = (
        db.query(ChatConversation)
        .filter(
            ChatConversation.id == convo_id,
            ChatConversation.user_id == user_id,
            ChatConversation.org_id == org_id,
        )
        .first()
    )
    if not convo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return convo


@router.get("/conversations", response_model=List[ChatConversationListItem])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id: UUID = Depends(require_org),
):
    return (
        db.query(ChatConversation)
        .filter(ChatConversation.user_id == current_user.id, ChatConversation.org_id == org_id)
        .order_by(ChatConversation.updated_at.desc())
        .all()
    )


@router.get("/conversations/{conversation_id}", response_model=ChatConversationResponse)
def get_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id: UUID = Depends(require_org),
):
    return get_conversation_or_404(db, conversation_id, current_user.id, org_id)


@router.post("/conversations", response_model=ChatConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ChatConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id: UUID = Depends(require_org),
):
    title = payload.title or "New conversation"
    convo = ChatConversation(
        org_id=org_id,
        user_id=current_user.id,
        title=title,
        messages=payload.messages,
    )
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


@router.put("/conversations/{conversation_id}", response_model=ChatConversationResponse)
def update_conversation(
    conversation_id: UUID,
    payload: ChatConversationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id: UUID = Depends(require_org),
):
    convo = get_conversation_or_404(db, conversation_id, current_user.id, org_id)
    if payload.title is not None:
        convo.title = payload.title
    if payload.messages is not None:
        convo.messages = payload.messages
    db.commit()
    db.refresh(convo)
    return convo


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id: UUID = Depends(require_org),
):
    convo = get_conversation_or_404(db, conversation_id, current_user.id, org_id)
    db.delete(convo)
    db.commit()
