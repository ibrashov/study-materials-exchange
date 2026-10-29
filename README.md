# Study Materials Exchange

A Basics of Information Systems semester project intended to help university students share and find study materials. Planned features include registration and login, uploading, searching by title, category or course, viewing and downloading materials.

## Team

| Member | Role |
| --- | --- |
| Ibrashov Anuar | Project Manager & System Analyst |
| Kozhakhmetov Talgat | Database & Backend Developer |
| Ainakul Arnur | Admin Panel & Testing Developer |
| Abylay Daryn | File Management & Search Developer |
| Anuarbek Alibek | Frontend & Multilanguage Developer |

## Status

Week 9 — Database Design. SQLite is selected for initial database prototyping. This repository contains an initial schema, fictional sample data, a reporting query, tests and documentation. The application, authentication, upload and search functionality are not yet implemented.

## Explore

Read [requirements](docs/requirements.md), the [ER diagram](database/ERD.md), and [progress report](docs/TASK09_PROGRESS.md). SQL scripts are in `database/`. Run the database tests from the repository root with `python -m unittest discover -s tests -v`. Each SQLite connection must enable `PRAGMA foreign_keys = ON` before use; this setting is per connection.
