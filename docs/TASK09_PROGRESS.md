# Task 9 — Database project check

## Purpose and main action

Study Materials Exchange aims to let students find and share course resources. The main planned action is an authenticated student uploading a file with metadata for others to find. Week 9 focuses on designing and prototyping its database.

## Progress

Earlier academic work described requirements and acceptance criteria (Task 4), scanning and uploading using a laptop, scanner or smartphone (Task 5), automatic backup as a security priority (Task 6), and data quality risks (Task 7). This repository now contains a four-table SQLite schema, a Mermaid ERD, fictional sample metadata and a query counting materials by course, including zero counts. No actual files or credentials are included.

`python -m unittest discover -s tests -v` was executed: **7 tests passed**. These use an in-memory database and check schema creation, sample insertion, query results, duplicate emails, blank titles, foreign keys, file-size boundaries and roles. This does not test application features or production performance.

## Unfinished

Full authentication, real file uploading, a complete frontend, backend API, admin dashboard and production backup system are **not implemented**. Search, download, authorization, actual file validation, deployment and performance testing also remain to be implemented. The password hash in the sample is an unusable placeholder.

## Risk and proposed solution

A material record could be created when its file upload fails. In future, verify that the file was stored before finalizing the record, handle errors and clean up incomplete files or database entries. A SQL rollback cannot undo a file system operation, so compensating cleanup is required. Enable SQLite foreign keys for every connection. Automatic backups and restoration tests remain a future priority.

## Next steps and responsibilities

- **Ibrashov Anuar — Project Manager & System Analyst:** coordinate work, refine requirements and acceptance criteria, and track progress.
- **Kozhakhmetov Talgat — Database & Backend Developer:** review the schema and build the backend and authentication with per-connection foreign keys.
- **Ainakul Arnur — Admin Panel & Testing Developer:** plan the admin interface and extend integration and negative tests.
- **Abylay Daryn — File Management & Search Developer:** design safe file storage, failure cleanup, upload validation and search.
- **Anuarbek Alibek — Frontend & Multilanguage Developer:** design the interface and multilingual support around the agreed workflows.

Review these assignments with the team, then implement and test the upload workflow, search, authorization and backup/restore procedures incrementally.
