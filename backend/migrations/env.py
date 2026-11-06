from alembic import context
from backend.app.core.config import settings
from backend.app.db.session import engine_for
from backend.app.models.entities import Base
if not settings.database_url:
    raise RuntimeError('Set DATABASE_URL in backend/.env before migrating')
if context.is_offline_mode():
    context.configure(url=settings.database_url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine_for(settings.database_url).connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
