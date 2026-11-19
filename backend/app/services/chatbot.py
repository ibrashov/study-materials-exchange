"""Study assistant: forwards a short conversation to the Anthropic Messages API.

The API key lives only on the server (backend/.env: ANTHROPIC_API_KEY). Without a key the
feature is switched off and the frontend hides the chat window.
"""
import logging

import httpx

from ..core.config import settings

log = logging.getLogger(__name__)

API_URL = 'https://api.anthropic.com/v1/messages'
ANTHROPIC_VERSION = '2023-06-01'
SYSTEM_PROMPT = (
    'You are a study assistant for Study Materials Exchange, a university platform where students share '
    'course notes as PDF files. Help with studying: explain concepts, plan revision, and suggest search terms '
    'for finding materials on the platform. You cannot see the platform\'s files or user accounts. '
    'Answer in the language the user writes in.'
)


class ChatbotError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def enabled() -> bool:
    return bool(settings.anthropic_api_key.strip())


def ask(messages: list[dict]) -> str:
    """messages: [{'role': 'user'|'assistant', 'content': str}], last one from the user."""
    if not enabled():
        raise ChatbotError(503, 'Chatbot is not configured. Set ANTHROPIC_API_KEY in backend/.env.')
    # The Messages API expects the conversation to start with a user turn.
    while messages and messages[0]['role'] == 'assistant':
        messages = messages[1:]
    try:
        response = httpx.post(
            API_URL,
            timeout=30,
            headers={
                'x-api-key': settings.anthropic_api_key.strip(),
                'anthropic-version': ANTHROPIC_VERSION,
                'content-type': 'application/json',
            },
            json={
                'model': settings.chatbot_model,
                'max_tokens': settings.chatbot_max_tokens,
                'system': SYSTEM_PROMPT,
                'messages': messages,
            },
        )
    except httpx.HTTPError as error:
        log.warning('Chatbot request failed: %s', type(error).__name__)
        raise ChatbotError(503, 'Chatbot service is unreachable')
    if response.status_code != 200:
        # Log only the status: the upstream body may echo details we do not want to show users.
        log.warning('Chatbot upstream returned HTTP %s', response.status_code)
        raise ChatbotError(503, 'Chatbot request failed')
    parts = [block.get('text', '') for block in response.json().get('content', []) if block.get('type') == 'text']
    return ''.join(parts).strip() or 'No answer was returned.'
