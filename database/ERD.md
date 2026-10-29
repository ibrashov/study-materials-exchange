# Initial entity relationship diagram

```mermaid
erDiagram
    users ||--o{ materials : uploads
    categories ||--o{ materials : classifies
    courses ||--o{ materials : contains
    users {
        INTEGER user_id PK
        TEXT full_name
        TEXT email UK
        TEXT password_hash
        TEXT role
    }
    categories {
        INTEGER category_id PK
        TEXT category_name UK
        TEXT description
        TEXT created_at
    }
    courses {
        INTEGER course_id PK
        TEXT course_name
        TEXT course_code UK
        TEXT description
    }
    materials {
        INTEGER material_id PK
        INTEGER uploader_id FK
        INTEGER category_id FK
        INTEGER course_id FK
        TEXT title
        TEXT file_path
        INTEGER file_size_bytes
        TEXT uploaded_at
    }
```

Each material belongs to one user, category and course; each of those can have many materials. Separate tables avoid repeating user, category and course details in every material, reducing duplication and inconsistent updates. The database holds file metadata and paths, not file blobs. `password_hash` is reserved for future authentication. Application logic must enforce authorization; a foreign key alone cannot establish that an uploader is authenticated. SQLite foreign key enforcement must be enabled on every connection.
