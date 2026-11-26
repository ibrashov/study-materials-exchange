"""Read-only database tools the study assistant may call.

Each tool returns plain dicts with only public catalogue fields. Emails, password hashes,
TOTP secrets and internal file paths are never selected, so the model cannot repeat them.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.entities import Category, Course, Material, User

MAX_RESULTS = 20


def _clamp(value, default: int = 10) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(1, min(number, MAX_RESULTS))


def _like_pattern(text: str) -> str:
    escaped = text.replace('\\', '\\\\').replace('%', r'\%').replace('_', r'\_')
    return f'%{escaped}%'


def get_platform_overview(db: Session) -> dict:
    return {
        'materials': db.scalar(select(func.count()).select_from(Material).where(Material.deleted_at.is_(None))),
        'courses': db.scalar(select(func.count()).select_from(Course)),
        'categories': db.scalar(select(func.count()).select_from(Category)),
        'students_registered': db.scalar(select(func.count()).select_from(User).where(User.role == 'student')),
        'total_downloads': db.scalar(
            select(func.coalesce(func.sum(Material.download_count), 0)).where(Material.deleted_at.is_(None))
        ),
    }


def list_categories(db: Session) -> list[dict]:
    rows = db.execute(
        select(Category.category_name, Category.description, func.count(Material.material_id))
        .outerjoin(Material, (Material.category_id == Category.category_id) & Material.deleted_at.is_(None))
        .group_by(Category.category_id, Category.category_name, Category.description)
        .order_by(Category.category_name)
    ).all()
    return [{'name': name, 'description': desc, 'materials': count} for name, desc, count in rows]


def list_courses(db: Session) -> list[dict]:
    rows = db.execute(
        select(Course.course_code, Course.course_name, Course.description, func.count(Material.material_id))
        .outerjoin(Material, (Material.course_id == Course.course_id) & Material.deleted_at.is_(None))
        .group_by(Course.course_id, Course.course_code, Course.course_name, Course.description)
        .order_by(Course.course_code)
    ).all()
    return [{'code': code, 'name': name, 'description': desc, 'materials': count} for code, name, desc, count in rows]


def search_materials(db: Session, query: str = '', course_code: str = '', category_name: str = '', limit=10) -> list[dict]:
    statement = (
        select(Material.material_id, Material.title, Material.uploaded_at, Material.download_count,
               Course.course_code, Course.course_name, Category.category_name)
        .join(Course, Course.course_id == Material.course_id)
        .join(Category, Category.category_id == Material.category_id)
        .where(Material.deleted_at.is_(None))
    )
    if query.strip():
        statement = statement.where(Material.title.ilike(_like_pattern(query.strip()), escape='\\'))
    if course_code.strip():
        statement = statement.where(Course.course_code == course_code.strip())
    if category_name.strip():
        statement = statement.where(Category.category_name == category_name.strip())
    statement = statement.order_by(Material.material_id.desc()).limit(_clamp(limit))
    return [
        {
            'id': material_id,
            'title': title,
            'uploaded_at': uploaded_at.isoformat() if uploaded_at else None,
            'downloads': downloads,
            'course_code': code,
            'course_name': course_name,
            'category': category,
        }
        for material_id, title, uploaded_at, downloads, code, course_name, category in db.execute(statement).all()
    ]


TOOL_FUNCTIONS = {
    'get_platform_overview': lambda db, args: get_platform_overview(db),
    'list_categories': lambda db, args: list_categories(db),
    'list_courses': lambda db, args: list_courses(db),
    'search_materials': lambda db, args: search_materials(
        db,
        query=str(args.get('query', '')),
        course_code=str(args.get('course_code', '')),
        category_name=str(args.get('category_name', '')),
        limit=args.get('limit', 10),
    ),
}

# Gemini function declarations (OpenAPI-style schema).
FUNCTION_DECLARATIONS = [
    {
        'name': 'get_platform_overview',
        'description': 'Get totals: number of study materials, courses, categories, registered students and downloads.',
        'parameters': {'type': 'OBJECT', 'properties': {}},
    },
    {
        'name': 'list_categories',
        'description': 'List all material categories with descriptions and how many materials each contains.',
        'parameters': {'type': 'OBJECT', 'properties': {}},
    },
    {
        'name': 'list_courses',
        'description': 'List all courses with their codes, names, descriptions and how many materials each has.',
        'parameters': {'type': 'OBJECT', 'properties': {}},
    },
    {
        'name': 'search_materials',
        'description': 'Search uploaded study materials by title keyword, optionally filtered by course code or category name. Returns up to 20 newest matches.',
        'parameters': {
            'type': 'OBJECT',
            'properties': {
                'query': {'type': 'STRING', 'description': 'Words to find in the material title. Leave empty to list recent materials.'},
                'course_code': {'type': 'STRING', 'description': 'Exact course code, e.g. CS101.'},
                'category_name': {'type': 'STRING', 'description': 'Exact category name.'},
                'limit': {'type': 'INTEGER', 'description': 'Maximum results, 1 to 20.'},
            },
        },
    },
]


def run_tool(db: Session, name: str, args: dict) -> dict:
    """Run one tool by name. Unknown names return an error object instead of raising."""
    function = TOOL_FUNCTIONS.get(name)
    if function is None:
        return {'error': f'Unknown tool: {name}'}
    try:
        return {'result': function(db, args or {})}
    except Exception:
        db.rollback()
        return {'error': 'The tool failed to read the database.'}
