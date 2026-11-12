from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    __table_args__ = (CheckConstraint("role IN ('student', 'admin')", name='ck_users_role'),)
    user_id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(10), default='student')
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text('true'))
    # Week 11: TOTP two-factor authentication; the secret is stored encrypted (services/twofactor.py).
    totp_secret: Mapped[str | None] = mapped_column(Text)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text('false'))

class Category(Base):
    __tablename__ = 'categories'
    category_id: Mapped[int] = mapped_column(primary_key=True)
    __table_args__ = (Index('ix_categories_name_trgm', 'category_name', postgresql_using='gin',
                            postgresql_ops={'category_name': 'gin_trgm_ops'}),)
    category_name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Course(Base):
    __tablename__ = 'courses'
    course_id: Mapped[int] = mapped_column(primary_key=True)
    __table_args__ = (Index('ix_courses_name_trgm', 'course_name', postgresql_using='gin',
                            postgresql_ops={'course_name': 'gin_trgm_ops'}),)
    course_name: Mapped[str] = mapped_column(String(150))
    course_code: Mapped[str] = mapped_column(String(30), unique=True)
    description: Mapped[str | None] = mapped_column(Text)

class Material(Base):
    __tablename__ = 'materials'
    __table_args__ = (
        CheckConstraint("length(btrim(title, E' \t\n\r')) > 0", name='ck_materials_title'),
        CheckConstraint('file_size_bytes BETWEEN 1 AND 52428800', name='ck_materials_size'),
        # Week 11: list pages filter by course/category and sort by newest id; title search uses trigrams.
        Index('ix_materials_course_newest', 'course_id', text('material_id DESC')),
        Index('ix_materials_category_newest', 'category_id', text('material_id DESC')),
        Index('ix_materials_title_trgm', 'title', postgresql_using='gin', postgresql_ops={'title': 'gin_trgm_ops'}),
    )
    material_id: Mapped[int] = mapped_column(primary_key=True)
    uploader_id: Mapped[int] = mapped_column(ForeignKey('users.user_id'), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey('categories.category_id'))
    course_id: Mapped[int] = mapped_column(ForeignKey('courses.course_id'))
    title: Mapped[str] = mapped_column(String(200))
    file_path: Mapped[str] = mapped_column(Text)
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    download_count: Mapped[int] = mapped_column(Integer, server_default=text('0'))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
