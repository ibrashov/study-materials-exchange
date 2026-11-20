"""Study assistant AI Agent: configurable Anthropic Messages API with live platform tools.

The API key lives only on the server (backend/.env: ANTHROPIC_API_KEY). Without a key the
feature is switched off and the frontend hides the chat window.
When tools are enabled, the agent can search real study materials, list courses/categories,
check the signed-in user's gamification progress, view the leaderboard, and inspect their trash.
"""
import json
import logging
import httpx
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models.entities import Category, Course, Material, User
from . import gamification
from .app_settings import get_json_setting, set_json_setting

log = logging.getLogger(__name__)

API_URL = 'https://api.anthropic.com/v1/messages'
ANTHROPIC_VERSION = '2023-06-01'
SETTING_KEY = 'agent_config'

DEFAULT_SYSTEM_PROMPT = (
    'You are an AI Study Assistant Agent for Study Materials Exchange, a university platform where students '
    'share course notes as PDF files. Help with studying: explain concepts, plan revision, and use your tools '
    'to search real materials on the platform, list courses and categories, check the student\'s gamification '
    'progress (XP, level, badges, streak), view the leaderboard, or inspect their Trash bin when asked. '
    'Never invent materials that do not exist in tool results. Answer in the language the user writes in.'
)

# Legacy alias preserved for any external imports.
SYSTEM_PROMPT = DEFAULT_SYSTEM_PROMPT

TOOL_DEFINITIONS: dict[str, dict] = {
    'search_materials': {
        'name': 'search_materials',
        'description': 'Search active study materials on the platform by keyword, course code, or category name.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'query': {'type': 'string', 'description': 'Search keyword for title, course, or category'},
                'course_code': {'type': 'string', 'description': 'Optional exact course code like PROG101'},
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': 10, 'default': 5},
            },
        },
    },
    'list_courses_and_categories': {
        'name': 'list_courses_and_categories',
        'description': 'List all available courses and categories along with how many active materials each has.',
        'input_schema': {'type': 'object', 'properties': {}},
    },
    'get_my_progress': {
        'name': 'get_my_progress',
        'description': 'Get the current signed-in user\'s gamification progress: XP, level, streak, badges, and uploads.',
        'input_schema': {'type': 'object', 'properties': {}},
    },
    'get_leaderboard': {
        'name': 'get_leaderboard',
        'description': 'Get the top contributors on the Study Materials Exchange gamification leaderboard.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': 10, 'default': 5},
            },
        },
    },
    'get_my_trash': {
        'name': 'get_my_trash',
        'description': 'List study materials currently in the signed-in user\'s Trash bin that can be restored.',
        'input_schema': {'type': 'object', 'properties': {}},
    },
}

ALL_TOOL_NAMES = list(TOOL_DEFINITIONS.keys())


class ChatbotError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def enabled() -> bool:
    return bool(settings.anthropic_api_key.strip())


def default_agent_config() -> dict:
    return {
        'model': settings.chatbot_model,
        'max_tokens': int(settings.chatbot_max_tokens),
        'temperature': float(settings.chatbot_temperature),
        'tools_enabled': bool(settings.chatbot_tools_enabled),
        'max_tool_steps': int(settings.chatbot_max_tool_steps),
        'system_prompt': settings.chatbot_system_prompt.strip() or DEFAULT_SYSTEM_PROMPT,
        'enabled_tools': list(ALL_TOOL_NAMES),
    }


def load_agent_config(db: Session | None) -> dict:
    defaults = default_agent_config()
    if db is None:
        return defaults
    try:
        raw = get_json_setting(db, SETTING_KEY, defaults)
    except Exception:
        return defaults
    valid_tools = [name for name in raw.get('enabled_tools', ALL_TOOL_NAMES) if name in TOOL_DEFINITIONS]
    prompt = str(raw.get('system_prompt') or '').strip() or DEFAULT_SYSTEM_PROMPT
    return {
        'model': str(raw.get('model') or defaults['model']).strip() or defaults['model'],
        'max_tokens': max(64, min(4000, int(raw.get('max_tokens', defaults['max_tokens'])))),
        'temperature': max(0.0, min(1.0, float(raw.get('temperature', defaults['temperature'])))),
        'tools_enabled': bool(raw.get('tools_enabled', defaults['tools_enabled'])),
        'max_tool_steps': max(1, min(8, int(raw.get('max_tool_steps', defaults['max_tool_steps'])))),
        'system_prompt': prompt,
        'enabled_tools': valid_tools,
    }


def save_agent_config(db: Session, updates: dict) -> dict:
    current = load_agent_config(db)
    for key in ('model', 'max_tokens', 'temperature', 'tools_enabled', 'max_tool_steps', 'system_prompt', 'enabled_tools'):
        if key in updates and updates[key] is not None:
            current[key] = updates[key]
    current['enabled_tools'] = [name for name in current['enabled_tools'] if name in TOOL_DEFINITIONS]
    if not str(current.get('system_prompt', '')).strip():
        current['system_prompt'] = DEFAULT_SYSTEM_PROMPT
    return set_json_setting(db, SETTING_KEY, current)


def execute_tool(name: str, tool_input: dict, db: Session | None, user: User | None) -> dict:
    """Execute one read-only agent tool safely scoped to the authenticated user."""
    if db is None:
        return {'error': 'Database session unavailable for tool execution'}

    if name == 'search_materials':
        q = str((tool_input or {}).get('query') or '').strip()
        course_code = str((tool_input or {}).get('course_code') or '').strip().upper()
        limit = max(1, min(10, int((tool_input or {}).get('limit') or 5)))

        query = (
            select(
                Material.material_id,
                Material.title,
                Material.download_count,
                Course.course_code,
                Course.course_name,
                Category.category_name,
            )
            .join(Course, Course.course_id == Material.course_id)
            .join(Category, Category.category_id == Material.category_id)
            .where(Material.deleted_at.is_(None))
        )
        if q:
            query = query.where(
                or_(
                    Material.title.icontains(q, autoescape=True),
                    Course.course_name.icontains(q, autoescape=True),
                    Category.category_name.icontains(q, autoescape=True),
                )
            )
        if course_code:
            query = query.where(func.upper(Course.course_code) == course_code)
        rows = db.execute(query.order_by(Material.download_count.desc(), Material.material_id.desc()).limit(limit)).all()
        return {
            'count': len(rows),
            'materials': [
                {
                    'material_id': r.material_id,
                    'title': r.title,
                    'course_code': r.course_code,
                    'course_name': r.course_name,
                    'category': r.category_name,
                    'downloads': r.download_count,
                }
                for r in rows
            ],
        }

    if name == 'list_courses_and_categories':
        courses = db.execute(
            select(
                Course.course_code,
                Course.course_name,
                func.count(Material.material_id).label('material_count'),
            )
            .outerjoin(Material, (Material.course_id == Course.course_id) & (Material.deleted_at.is_(None)))
            .group_by(Course.course_id)
            .order_by(Course.course_code)
        ).all()
        categories = db.scalars(select(Category.category_name).order_by(Category.category_name)).all()
        return {
            'courses': [
                {'code': c.course_code, 'name': c.course_name, 'materials': int(c.material_count)}
                for c in courses
            ],
            'categories': list(categories),
        }

    if name == 'get_my_progress':
        if user is None or not hasattr(user, 'user_id'):
            return {'error': 'User profile unavailable'}
        db_user = db.get(User, user.user_id)
        if db_user is None:
            return {'error': 'User profile unavailable'}
        profile = gamification.get_user_profile(db, db_user)
        return {
            'full_name': profile['full_name'],
            'xp_points': profile['xp_points'],
            'level': profile['level'],
            'level_code': profile['level_code'],
            'next_level_xp': profile['next_level_xp'],
            'current_streak': profile['current_streak'],
            'longest_streak': profile['longest_streak'],
            'materials_count': profile['materials_count'],
            'total_downloads_received': profile['total_downloads_received'],
            'earned_badges': [b['code'] for b in profile['badges'] if b['earned']],
        }

    if name == 'get_leaderboard':
        limit = max(1, min(10, int((tool_input or {}).get('limit') or 5)))
        return {'leaderboard': gamification.get_leaderboard(db, limit=limit)}

    if name == 'get_my_trash':
        if user is None or not hasattr(user, 'user_id'):
            return {'error': 'User unavailable'}
        q = select(Material).where(Material.deleted_at.is_not(None))
        if getattr(user, 'role', 'student') != 'admin':
            q = q.where(Material.uploader_id == user.user_id)
        rows = db.scalars(q.order_by(Material.deleted_at.desc()).limit(20)).all()
        return {
            'count': len(rows),
            'items': [
                {
                    'material_id': m.material_id,
                    'title': m.title,
                    'deleted_at': m.deleted_at.isoformat() if m.deleted_at else None,
                }
                for m in rows
            ],
        }

    return {'error': f'Unknown tool: {name}'}


def _call_anthropic(payload: dict) -> dict:
    try:
        response = httpx.post(
            API_URL,
            timeout=30,
            headers={
                'x-api-key': settings.anthropic_api_key.strip(),
                'anthropic-version': ANTHROPIC_VERSION,
                'content-type': 'application/json',
            },
            json=payload,
        )
    except httpx.HTTPError as error:
        log.warning('Chatbot request failed: %s', type(error).__name__)
        raise ChatbotError(503, 'Chatbot service is unreachable')
    if response.status_code != 200:
        # Log only the status: the upstream body may echo details we do not want to show users.
        log.warning('Chatbot upstream returned HTTP %s', response.status_code)
        raise ChatbotError(503, 'Chatbot request failed')
    return response.json()


def ask_agent(messages: list[dict], *, db: Session | None = None, user: User | None = None) -> dict:
    """Run the configurable AI Agent (with optional tool-calling loop) and return reply + metadata."""
    if not enabled():
        raise ChatbotError(503, 'Chatbot is not configured. Set ANTHROPIC_API_KEY in backend/.env.')

    config = load_agent_config(db)
    # The Messages API expects the conversation to start with a user turn.
    conversation = list(messages)
    while conversation and conversation[0]['role'] == 'assistant':
        conversation = conversation[1:]

    active_tools = (
        [TOOL_DEFINITIONS[name] for name in config['enabled_tools'] if name in TOOL_DEFINITIONS]
        if config['tools_enabled'] and db is not None
        else []
    )

    tools_used: list[str] = []
    max_steps = int(config['max_tool_steps']) if active_tools else 1
    data: dict = {}

    for _step in range(max_steps):
        payload = {
            'model': config['model'],
            'max_tokens': config['max_tokens'],
            'system': config['system_prompt'],
            'messages': conversation,
        }
        if active_tools:
            payload['tools'] = active_tools
            payload['temperature'] = config['temperature']

        data = _call_anthropic(payload)
        content_blocks = data.get('content', [])
        tool_uses = [block for block in content_blocks if block.get('type') == 'tool_use']

        if not tool_uses or not active_tools:
            break

        conversation.append({'role': 'assistant', 'content': content_blocks})
        tool_results = []
        for call in tool_uses:
            tool_name = str(call.get('name', ''))
            if tool_name not in config['enabled_tools']:
                result = {'error': f'Tool {tool_name} is disabled'}
            else:
                tools_used.append(tool_name)
                result = execute_tool(tool_name, call.get('input') or {}, db, user)
            tool_results.append({
                'type': 'tool_result',
                'tool_use_id': call.get('id', ''),
                'content': json.dumps(result, ensure_ascii=False),
            })
        conversation.append({'role': 'user', 'content': tool_results})

    parts = [block.get('text', '') for block in data.get('content', []) if block.get('type') == 'text']
    reply = ''.join(parts).strip() or 'No answer was returned.'

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

    return {
        'reply': reply,
        'tools_used': tools_used,
        'model': config['model'],
    }


def ask(messages: list[dict], *, db: Session | None = None, user: User | None = None) -> str:
    """Backward-compatible helper returning only the assistant text reply."""
    return ask_agent(messages, db=db, user=user)['reply']
