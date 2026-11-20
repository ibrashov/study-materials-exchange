from contextlib import contextmanager
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ...core.config import settings
from ...db.session import get_db
from ...models.entities import User
from ...services import chatbot
from ..dependencies import current_user

router = APIRouter(tags=['chat'])


class ChatMessage(BaseModel):
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)
    include_meta: bool = False


@contextmanager
def optional_db(request: Request, user: User):
    """Open a DB session only when a real database/override is available for a real user."""
    if not hasattr(user, 'user_id'):
        yield None
        return
    override = request.app.dependency_overrides.get(get_db)
    if override is not None:
        gen = override()
        if hasattr(gen, '__next__'):
            db = next(gen)
            try:
                yield db
            finally:
                try:
                    next(gen)
                except StopIteration:
                    pass
            return
        yield gen
        return
    if not settings.database_url:
        yield None
        return
    gen = get_db()
    db = next(gen)
    try:
        yield db
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.get('/chat/status')
def chat_status(_user: User = Depends(current_user)):
    return {'enabled': chatbot.enabled()}


@router.get('/chat/agent')
def chat_agent_info(request: Request, user: User = Depends(current_user)):
    with optional_db(request, user) as db:
        cfg = chatbot.load_agent_config(db)
    return {
        'enabled': chatbot.enabled(),
        'model': cfg['model'],
        'tools_enabled': cfg['tools_enabled'],
        'active_tools': cfg['enabled_tools'] if cfg['tools_enabled'] else [],
        'max_tool_steps': cfg['max_tool_steps'],
    }


@router.post('/chat')
def chat(body: ChatRequest, request: Request, user: User = Depends(current_user)):
    if body.messages[-1].role != 'user':
        raise HTTPException(400, 'The last message must come from the user')
    try:
        with optional_db(request, user) as db:
            result = chatbot.ask_agent([m.model_dump() for m in body.messages], db=db, user=user)
    except chatbot.ChatbotError as error:
        raise HTTPException(error.status, error.message)
    if body.include_meta:
        return result
    return {'reply': result['reply']}
