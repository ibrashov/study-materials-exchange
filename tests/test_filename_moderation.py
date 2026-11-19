"""Phase 10: Comprehensive unit and real PostgreSQL integration tests for ML filename moderation."""

from __future__ import annotations

import io
from pathlib import Path
import tempfile
import unittest

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.session import engine_for, get_db
from backend.app.main import app
from backend.app.models.entities import Category, Course, Material, User
from backend.app.services.auth import hasher
from backend.app.services.ratelimit import limiter
from ml_moderation.config import DEFAULT_MODEL_PATH, MAX_INPUT_LENGTH, REJECTION_MESSAGE
from ml_moderation.normalization import normalize_text
from ml_moderation.predictor import (
    FilenameModerator,
    ModerationModelLoadError,
    get_moderator,
    reset_moderator_cache,
)

PASSWORD = "Test-password-123!"


def pdf_bytes() -> bytes:
    buf = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(buf)
    return buf.getvalue()


class NormalizationAndModelUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.moderator = get_moderator(DEFAULT_MODEL_PATH)

    def test_valid_english_filenames_allowed(self) -> None:
        samples = [
            "Deep_Learning_Week12.pdf",
            "Linear_Algebra_Lecture_04.pdf",
            "Software_Engineering_Final_Report.pdf",
            "PostgreSQL_Indexing_Notes.pdf",
            "../../notes.pdf",
        ]
        for fname in samples:
            dec = self.moderator.moderate(fname)
            self.assertTrue(dec.allowed, f"Expected ALLOWED for {fname}, got {dec}")

    def test_valid_russian_filenames_allowed(self) -> None:
        samples = [
            "Лекция_математика.pdf",
            "Конспект_алгоритмы_неделя_12.pdf",
            "Лабораторная_базы_данных_3.pdf",
            "Таблица_интегралов.pdf",
            "Учебник_по_экономике.pdf",
            "Расписание_экзаменов.pdf",
        ]
        for fname in samples:
            dec = self.moderator.moderate(fname)
            self.assertTrue(dec.allowed, f"Expected ALLOWED for {fname}, got {dec}")

    def test_valid_kazakh_filenames_allowed(self) -> None:
        samples = [
            "Қазақстан_тарихы.pdf",
            "Ақпараттық_жүйелер_дәріс_12.pdf",
            "Қорытынды_емтихан_2026.pdf",
            "Қосымша_тапсырма_12.pdf",
            "Көбейту_кестесі_алгоритм.pdf",
            "Сілтемелер_тізімі_реферат.pdf",
        ]
        for fname in samples:
            dec = self.moderator.moderate(fname)
            self.assertTrue(dec.allowed, f"Expected ALLOWED for {fname}, got {dec}")

    def test_hard_negatives_allowed(self) -> None:
        samples = [
            "Assignment_12.pdf",
            "Class_Notes.pdf",
            "Password_Security.pdf",
            "Pass_Exam.pdf",
            "Assistant_Guide.pdf",
            "Data_Classification.pdf",
            "pASS.pdf",
            "Mass_Spectrometry_Lab.pdf",
            "Grass_Biology_Fieldwork.pdf",
            "Linear_Regression_Analysis.pdf",
            "Document_Parsing_Guide.pdf",
            "Coursework_Final_Draft.pdf",
        ]
        for fname in samples:
            dec = self.moderator.moderate(fname)
            self.assertTrue(dec.allowed, f"Hard negative falsely blocked: {fname} -> {dec}")

    def test_explicit_prohibited_words_blocked(self) -> None:
        samples = [
            "ASS.pdf",
            "fuck_homework.pdf",
            "shit_lecture.pdf",
            "хуйня_лекция.pdf",
            "пиздец_экзамен.pdf",
            "блять_лаба.pdf",
            "қотақ_дәріс.pdf",
            "қотақбас_есеп.pdf",
            "сіктір_жұмыс.pdf",
        ]
        for fname in samples:
            dec = self.moderator.moderate(fname)
            self.assertFalse(dec.allowed, f"Expected BLOCKED for {fname}, got {dec}")
            self.assertEqual(dec.reason, "inappropriate_filename")

    def test_obfuscated_repeated_inserted_special_leet_unicode_mixed_blocked(self) -> None:
        cases = {
            "repeated": ["pppAAASSSS.pdf", "fuuuucking_notes.pdf", "бляяяять_курс.pdf", "қотаааақ.pdf"],
            "inserted": ["A123SS.pdf", "s456hit.pdf", "х123уй.pdf", "қ123отақ.pdf"],
            "special": ["@$$.pdf", "A.S.S.pdf", "A_S_S.pdf", "f_u_c_k_exam.pdf", "$h!t_slides.pdf", "қ_о_т_а_қ.pdf"],
            "leetspeak": ["f4ck_homework.pdf", "sh1t_lecture.pdf", "п1здец_отчет.pdf", "қ0тақ_тапсырма.pdf"],
            "unicode": ["ａｓｓ_homework.pdf", "ｆｕｃｋ_project.pdf", "f\u200bu\u200bc\u200bk.pdf", "қ\u200bо\u200bт\u200bа\u200bқ.pdf"],
            "mixed_script": ["аss_lecture.pdf", "fуck_lab3.pdf", "сyка_конспект.pdf", "қоtақ_test.pdf"],
        }
        for group, items in cases.items():
            for fname in items:
                dec = self.moderator.moderate(fname)
                self.assertFalse(dec.allowed, f"Expected BLOCKED [{group}] for {fname!r}, got {dec}")

    def test_empty_and_excessively_long_inputs(self) -> None:
        for empty in ("", "   ", None):
            dec = self.moderator.moderate(empty)
            self.assertTrue(dec.allowed)
            self.assertEqual(dec.reason, "empty_input")

        huge_clean = ("Algorithms_Lecture_" * 400) + ".pdf"
        self.assertGreater(len(huge_clean), MAX_INPUT_LENGTH)
        norm = normalize_text(huge_clean)
        self.assertTrue(norm.was_truncated)
        dec = self.moderator.moderate(huge_clean)
        self.assertTrue(dec.allowed)
        self.assertLess(dec.latency_ms, 100.0)

    def test_model_loading_failure_raises_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does_not_exist.joblib"
            with self.assertRaises(ModerationModelLoadError):
                FilenameModerator(missing)

            corrupt = Path(tmp) / "corrupt.joblib"
            corrupt.write_bytes(b"not-a-valid-joblib-artifact")
            with self.assertRaises(ModerationModelLoadError):
                FilenameModerator(corrupt)

    def test_internal_response_contract(self) -> None:
        dec = self.moderator.moderate("ASS.pdf")
        payload = dec.to_internal_dict()
        self.assertEqual(set(payload.keys()), {"allowed", "reason", "confidence", "model_version"})
        self.assertFalse(payload["allowed"])
        self.assertEqual(payload["reason"], "inappropriate_filename")
        self.assertGreaterEqual(payload["confidence"], 0.5)


class BackendModerationIntegrationTests(unittest.TestCase):
    """Real PostgreSQL + FastAPI integration tests for upload moderation."""

    @classmethod
    def setUpClass(cls) -> None:
        url = settings.test_database_url
        if not url:
            raise unittest.SkipTest("TEST_DATABASE_URL not configured; PostgreSQL integration tests skipped")
        parsed = make_url(url)
        if parsed.drivername != "postgresql+psycopg" or not (parsed.database or "").endswith("_test"):
            raise RuntimeError("Refusing non-PostgreSQL or non-_test database")
        cls.engine = engine_for(url)
        original = settings.database_url
        try:
            settings.database_url = url
            command.upgrade(Config("alembic.ini"), "head")
        finally:
            settings.database_url = original
        cls.password_hash = hasher.hash(PASSWORD)

    def setUp(self) -> None:
        limiter.reset()
        reset_moderator_cache()
        with self.engine.begin() as conn:
            conn.execute(text("TRUNCATE materials, users, categories, courses RESTART IDENTITY CASCADE"))
        self.temp = tempfile.TemporaryDirectory()
        self.prev_uploads = settings.uploads_dir
        self.prev_secret = settings.auth_secret
        self.prev_model_path = settings.moderation_model_path
        settings.uploads_dir = Path(self.temp.name)
        settings.auth_secret = "test-only-secret-that-is-long-enough-12345"
        settings.moderation_model_path = DEFAULT_MODEL_PATH

        def test_db():
            with Session(self.engine) as db:
                yield db

        app.dependency_overrides[get_db] = test_db
        self.client = TestClient(app)
        with Session(self.engine) as db:
            db.add_all([
                Category(category_name="Lecture Notes"),
                Course(course_code="BIS12", course_name="Information Systems"),
                User(full_name="Student One", email="student@example.com", password_hash=self.password_hash, role="student"),
            ])
            db.commit()

        login_resp = self.client.post("/api/auth/login", json={"email": "student@example.com", "password": PASSWORD})
        self.assertEqual(login_resp.status_code, 200)
        self.headers = {"Authorization": "Bearer " + login_resp.json()["access_token"]}

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()
        settings.uploads_dir = self.prev_uploads
        settings.auth_secret = self.prev_secret
        settings.moderation_model_path = self.prev_model_path
        reset_moderator_cache()
        self.temp.cleanup()

    def _upload(self, title: str, filename: str):
        return self.client.post(
            "/api/materials",
            headers=self.headers,
            data={"title": title, "category_id": "1", "course_id": "1"},
            files={"file": (filename, pdf_bytes(), "application/pdf")},
        )

    def test_valid_multilingual_and_hard_negative_uploads_succeed(self) -> None:
        for title, fname in [
            ("Assignment 12 — Data Classification", "Assignment_12.pdf"),
            ("Password Security Class Notes", "Password_Security.pdf"),
            ("Қазақстан тарихы 12-апта", "Қазақстан_тарихы.pdf"),
            ("Лекция по высшей математике", "Лекция_математика.pdf"),
        ]:
            resp = self._upload(title, fname)
            self.assertEqual(resp.status_code, 201, f"Valid upload failed for {title}/{fname}: {resp.text}")
            self.assertEqual(resp.json()["title"], title)

        with Session(self.engine) as db:
            count = db.scalar(select(func.count()).select_from(Material))
        self.assertEqual(count, 4)
        self.assertEqual(len(list(Path(self.temp.name).glob("*.pdf"))), 4)

    def test_inappropriate_filename_or_title_rejected_with_zero_side_effects(self) -> None:
        bad_cases = [
            ("Normal Study Title", "ASS.pdf"),
            ("Normal Study Title", "pppAAASSSS.pdf"),
            ("Normal Study Title", "A.S.S.pdf"),
            ("Normal Study Title", "@$$.pdf"),
            ("Normal Study Title", "A123SS.pdf"),
            ("Normal Study Title", "қ0тақ_дәріс.pdf"),
            ("Normal Study Title", "п1здец_отчет.pdf"),
            ("f_u_c_k homework", "Assignment_12.pdf"),
            ("Қотақбас конспект", "Clean_Notes.pdf"),
        ]
        for title, fname in bad_cases:
            resp = self._upload(title, fname)
            self.assertEqual(resp.status_code, 422, f"Expected 422 for {title}/{fname}, got {resp.status_code}: {resp.text}")
            body = resp.json()
            self.assertEqual(body["error"]["code"], "http_422")
            self.assertEqual(body["error"]["message"], REJECTION_MESSAGE)

        # Verify zero permanent files and zero database rows were created.
        with Session(self.engine) as db:
            count = db.scalar(select(func.count()).select_from(Material))
        self.assertEqual(count, 0)
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_model_loading_failure_fails_closed_with_503(self) -> None:
        settings.moderation_model_path = Path(self.temp.name) / "missing_model.joblib"
        reset_moderator_cache()

        resp = self._upload("Assignment 12", "Assignment_12.pdf")
        self.assertEqual(resp.status_code, 503, resp.text)
        self.assertEqual(resp.json()["error"]["code"], "http_503")

        with Session(self.engine) as db:
            count = db.scalar(select(func.count()).select_from(Material))
        self.assertEqual(count, 0)
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
