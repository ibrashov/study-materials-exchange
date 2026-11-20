"""Study assistant chatbot powered by Google Gemini.

One API key, one fixed prompt, no tools and no admin configuration.
Set GEMINI_API_KEY in backend/.env (key from https://aistudio.google.com/apikey).
Without a key the feature stays switched off and the frontend hides the chat window.
"""
import logging
import time

import httpx
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models.entities import User
from . import gamification

log = logging.getLogger(__name__)

API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'

SYSTEM_PROMPT = (
    'You are the AI Study Assistant for Study Materials Exchange, a university platform where students '
    'share course notes as PDF files. Help with studying: explain concepts, summarize topics, and plan revision. '
    'Keep answers short and clear. Answer in the language the user writes in.'
)


class ChatbotError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def enabled() -> bool:
    return bool(settings.gemini_api_key.strip())


def ask(messages: list[dict], *, db: Session | None = None, user: User | None = None) -> str:
    """Send the conversation to Gemini and return the text reply."""
    if not enabled():
        raise ChatbotError(503, 'Chatbot is not configured. Set GEMINI_API_KEY in backend/.env.')

    # Gemini needs the conversation to start with a user turn and calls the assistant role "model".
    conversation = list(messages)
    while conversation and conversation[0]['role'] == 'assistant':
        conversation = conversation[1:]
    contents = [
        {'role': 'user' if m['role'] == 'user' else 'model', 'parts': [{'text': m['content']}]}
        for m in conversation
    ]

    body = {
        'systemInstruction': {'parts': [{'text': SYSTEM_PROMPT}]},
        'contents': contents,
        'generationConfig': {
            'maxOutputTokens': settings.chatbot_max_tokens,
            'temperature': settings.chatbot_temperature,
            'thinkingConfig': {'thinkingLevel': 'minimal'},  # fast replies; deep thinking made answers take 30-60 s
        },
    }
    # Gemini often answers 503 "high demand": retry the main model 3 times, then try a lighter one twice.
    models = [settings.gemini_model] * 3 + [settings.gemini_fallback_model] * 2
    response = None
    for attempt, model in enumerate(models):
        if attempt:
            time.sleep(min(attempt, 3))  # short backoff: 1 s, 2 s, 3 s, 3 s
        try:
            response = httpx.post(
                API_URL.format(model=model),
                timeout=30,
                headers={'x-goog-api-key': settings.gemini_api_key.strip(), 'Content-Type': 'application/json'},
                json=body,
            )
        except httpx.HTTPError as error:
            log.warning('Gemini request failed: %s', type(error).__name__)
            response = None
            continue
        if response.status_code not in (429, 500, 503):
            break
        log.warning('Gemini %s returned HTTP %s (attempt %s)', model, response.status_code, attempt + 1)
    if response is None:
        raise ChatbotError(503, 'Chatbot service is unreachable')
    if response.status_code != 200:
        # Log only the status: the upstream body may echo details we do not want to show users.
        log.warning('Gemini upstream returned HTTP %s', response.status_code)
        raise ChatbotError(503, 'The AI is busy right now, please try again in a moment')

    candidates = response.json().get('candidates') or []
    parts = ((candidates[0].get('content') or {}).get('parts') or []) if candidates else []
    reply = ''.join(part.get('text', '') for part in parts).strip() or 'No answer was returned.'

    # Award daily AI study session XP when running with a real DB user.
    if db is not None and user is not None and hasattr(user, 'user_id'):
        try:
            db_user = db.get(User, user.user_id)
            if db_user is not None:
                awarded = gamification.award_xp(
                    db, db_user, 'ai_study_session', 'Studied with AI Study Assistant', once_per_day=True
                )
                if awarded > 0:
                    db.commit()
        except Exception:
            db.rollback()

    return reply
