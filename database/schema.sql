-- Foreign key enforcement is per connection, including connections opened later.
PRAGMA foreign_keys = ON;

CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'admin'))
);

CREATE TABLE categories (
    category_id INTEGER PRIMARY KEY,
    category_name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE courses (
    course_id INTEGER PRIMARY KEY,
    course_name TEXT NOT NULL,
    course_code TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE materials (
    material_id INTEGER PRIMARY KEY,
    uploader_id INTEGER NOT NULL REFERENCES users(user_id),
    category_id INTEGER NOT NULL REFERENCES categories(category_id),
    course_id INTEGER NOT NULL REFERENCES courses(course_id),
    title TEXT NOT NULL CHECK (length(trim(title, char(9) || char(10) || char(13) || ' ')) > 0),
    file_path TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL CHECK (typeof(file_size_bytes) = 'integer' AND file_size_bytes BETWEEN 1 AND 52428800),
    uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
