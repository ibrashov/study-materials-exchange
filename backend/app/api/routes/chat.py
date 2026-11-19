from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ...models.entities import User
from ...services import chatbot
from ..dependencies import current_user

router = APIRouter(tags=['chat'])


class ChatMessage(BaseModel):
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)


@router.get('/chat/status')
def chat_status(_user: User = Depends(current_user)):
    return {'enabled': chatbot.enabled()}


@router.post('/chat')
def chat(body: ChatRequest, _user: User = Depends(current_user)):
    if body.messages[-1].role != 'user':
        raise HTTPException(400, 'The last message must come from the user')
    try:
        reply = chatbot.ask([m.model_dump() for m in body.messages])
    except chatbot.ChatbotError as error:
        raise HTTPException(error.status, error.message)
    return {'reply': reply}
