# System requirements

These are planned requirements, not claims of implemented application behavior.

**Main stakeholder:** University Student. Students need a reliable way to find and share course materials, which may otherwise be scattered across different channels. The business need is a centralized, searchable exchange that supports contributions while protecting data quality.

## Requirements

- **FR-01 — Registration and Login:** Students can create accounts and log in using email and password.
- **FR-02 — Search Materials:** Students can search by title, category or course name.
- **FR-03 — Upload Materials:** Authenticated students can upload a material with a title, category and file.
- **NFR-01 — Performance:** Search results should appear within 3 seconds under normal usage.
- **NFR-02 — File Upload:** Files up to 50 MB (52,428,800 bytes) must be supported.
- **BR-01:** Only authenticated students can upload. Guests may view and search, but cannot upload.

## Planned upload workflow

1. Student registers and logs in.
2. Student chooses a study material, enters its title and category, and selects a file. Selecting a course is a proposed extension to the earlier upload requirements.
3. The system checks the input and file size, stores the file and metadata, and makes the material discoverable through search.

Acceptance criteria: an authenticated student providing valid required metadata and a file of 1–52,428,800 bytes can submit it; once stored successfully, the material is searchable. Invalid or missing input and files over the limit are rejected with feedback. Negative case: a guest attempting an upload is denied and no file or material record is created. These scenarios require future application tests.

## Database traceability

| Requirement | Proposed table support | Additional work |
| --- | --- | --- |
| FR-01 | `users` stores email and a future password hash | Registration, password hashing and login |
| FR-02 | `materials`, `categories`, `courses` store searchable metadata | Search implementation and performance measurement for NFR-01 |
| FR-03, BR-01 | `materials` references `users` and `categories`; `courses` supports the proposed extension | Application authentication, authorization and file storage |
| NFR-02 | `materials.file_size_bytes` constrains metadata to 1–52,428,800 bytes | Validate actual uploaded file size |

Task 4 established requirements and acceptance criteria; Task 5 considered scanning and uploading from laptops, scanners and smartphones; Task 6 prioritized automatic backups; Task 7 addressed incorrect, missing, duplicate and inconsistent data. Backup and broader validation remain future work. Foreign keys and constraints support data quality but do not enforce login or upload permissions. Application logic must enforce authorization.
