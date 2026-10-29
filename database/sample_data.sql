-- Fictional metadata only. The placeholder is not a usable password hash or file.
INSERT INTO users (user_id, full_name, email, password_hash, role)
VALUES (1, 'Example Student', 'student@example.test', 'NOT-A-REAL-HASH', 'student');

INSERT INTO categories (category_id, category_name, description) VALUES
    (1, 'Notes', 'Course notes'),
    (2, 'Presentations', 'Presentation slides');

INSERT INTO courses (course_id, course_name, course_code) VALUES
    (1, 'Introduction to Programming', 'PROG101'),
    (2, 'Database Systems', 'DB101');

INSERT INTO materials (material_id, uploader_id, category_id, course_id, title, file_path, file_size_bytes)
VALUES (1, 1, 1, 1, 'Example programming notes', 'uploads/example-notes.pdf', 1024);
