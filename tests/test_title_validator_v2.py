import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import HTTPException
from pg_base import PostgresCase
from sqlalchemy import text

from backend.app.api.routes.materials import upload
from ml_moderation.validator_v2 import validate_title


class TitleValidatorUploadTests(PostgresCase):
    @patch.dict("os.environ", {"MATERIAL_VALIDATOR_V2_ENABLED": "true"})
    def test_same_pdf_title_is_rejected_or_saved_according_to_course(self):
        rejected = self.upload(title="SQL Joins and Queries", course_id=1)
        self.assertEqual(rejected.status_code, 422, rejected.text)
        self.assertEqual(self.stored_files(), [])
        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text("SELECT count(*) FROM materials")), 0)
            self.assertEqual(connection.scalar(text("SELECT count(*) FROM xp_events")), 0)
        accepted = self.upload(title="SQL Joins and Queries", course_id=2)
        self.assertEqual(accepted.status_code, 201, accepted.text)
        self.assertEqual(len(self.stored_files()), 1)
        self.assertEqual(accepted.json()["course_id"], 2)


class TitleValidatorTests(unittest.TestCase):
    def test_shadow_failure_does_not_log_title_or_block_upload(self):
        from backend.app.services.title_validation import enforce_title_validation
        course = SimpleNamespace(course_code="DB101", course_name="Database Systems", description=None)
        title = "SQL Joins and Queries"
        with patch.dict("os.environ", {"MATERIAL_VALIDATOR_V2_ENABLED": "true",
                                       "MATERIAL_VALIDATOR_V2_MODEL": "v2_2",
                                       "MATERIAL_VALIDATOR_V2_2_MODE": "shadow"}):
            with patch("ml_moderation.static_student.predict_student", side_effect=RuntimeError(title)):
                with self.assertLogs("backend.app.services.title_validation", level="WARNING") as logs:
                    enforce_title_validation(title, course)
        self.assertIn("RuntimeError", logs.output[0])
        self.assertNotIn(title, logs.output[0])

    def test_student_shadow_and_enforce_allow_semantic_uncertainty(self):
        from backend.app.services.title_validation import enforce_title_validation
        course = SimpleNamespace(course_code="DB101", course_name="Database Systems", description=None)
        with patch.dict("os.environ", {"MATERIAL_VALIDATOR_V2_ENABLED": "true",
                                       "MATERIAL_VALIDATOR_V2_MODEL": "v2_2"}):
            for mode, decision, rejected in (
                ("off", "IRRELEVANT_TITLE", False),
                ("shadow", "IRRELEVANT_TITLE", False),
                ("enforce", "INSUFFICIENT_CONTEXT", False),
                ("enforce", "IRRELEVANT_TITLE", True),
            ):
                with self.subTest(mode=mode, decision=decision), patch.dict(
                    "os.environ", {"MATERIAL_VALIDATOR_V2_2_MODE": mode}
                ), patch("ml_moderation.static_student.predict_student", return_value=decision) as model:
                    if rejected:
                        with self.assertRaises(HTTPException) as error:
                            enforce_title_validation("SQL Joins and Queries", course)
                        self.assertEqual(error.exception.status_code, 422)
                    else:
                        enforce_title_validation("SQL Joins and Queries", course)
                    self.assertEqual(model.call_count, int(mode != "off"))

    def test_preview_is_optional_and_has_explicit_rollback(self):
        from backend.app.services.title_validation import enforce_title_validation
        course = SimpleNamespace(course_code="DB101", course_name="Database Systems", description=None)
        title = "Storing an address only once when several orders share it"
        with patch("ml_moderation.semantic_preview.preview_decision", return_value="ACCEPTED") as preview:
            with patch.dict("os.environ", {
                "MATERIAL_VALIDATOR_V2_ENABLED": "true",
                "MATERIAL_VALIDATOR_V2_MODEL": "minilm_preview",
            }):
                enforce_title_validation(title, course)
            preview.assert_called_once_with(title, "DB101", "Database Systems", "IRRELEVANT_TITLE")
            with patch.dict("os.environ", {
                "MATERIAL_VALIDATOR_V2_ENABLED": "true",
                "MATERIAL_VALIDATOR_V2_MODEL": "v2_0",
            }):
                with self.assertRaises(HTTPException) as rejected:
                    enforce_title_validation(title, course)
            self.assertEqual(rejected.exception.status_code, 422)
            self.assertEqual(preview.call_count, 1)

    def test_title_is_evaluated_against_selected_course(self):
        for title in ("SQL", "Нормализация баз данных", "Деректер қорын басқару", "SQL сұраныстар"):
            with self.subTest(title=title):
                self.assertEqual(validate_title(title, "DB101", "Database Systems")[0], "ACCEPTED")
                self.assertEqual(
                    validate_title(title, "PROG101", "Introduction to Programming")[0], "IRRELEVANT_TITLE"
                )

    def test_policy(self):
        for title, expected in (
            ("Hello", "IRRELEVANT_TITLE"), ("Привет", "IRRELEVANT_TITLE"),
            ("Сәлем", "IRRELEVANT_TITLE"), ("Lecture 5", "INSUFFICIENT_CONTEXT"),
            ("asdfghjkl", "MEANINGLESS_TITLE"), ("аааааааааа", "MEANINGLESS_TITLE"),
            ("ＳＱＬ", "ACCEPTED"),
        ):
            with self.subTest(title=title):
                self.assertEqual(validate_title(title, "DB101", "Database Systems")[0], expected)
        self.assertEqual(validate_title("SQL", "NEW", "")[0], "INSUFFICIENT_CONTEXT")

    @patch.dict("os.environ", {"MATERIAL_VALIDATOR_V2_ENABLED": "true"})
    @patch("backend.app.api.routes.materials.gamification.award_xp")
    @patch("backend.app.api.routes.materials.save_pdf")
    def test_rejections_precede_side_effects(self, save_pdf, award_xp):
        course = SimpleNamespace(course_code="DB101", course_name="Database Systems", description=None)
        for title, filename, found, status in (
            ("Hello", "document_123.pdf", course, 422),
            ("SQL", "document_123.pdf", None, 422),
            ("SQL", "pppAAASSSS.pdf", course, 422),
        ):
            with self.subTest(title=title, filename=filename, found=found):
                db = Mock()
                db.get.side_effect = [object(), found]
                with self.assertRaises(HTTPException) as error:
                    upload(title, 1, 1, SimpleNamespace(filename=filename), Mock(), db)
                self.assertEqual(error.exception.status_code, status)
                save_pdf.assert_not_called()
                award_xp.assert_not_called()
                db.add.assert_not_called()
                db.commit.assert_not_called()

    @patch.dict("os.environ", {"MATERIAL_VALIDATOR_V2_ENABLED": "true"})
    def test_model_failure_maps_to_503(self):
        from backend.app.services.title_validation import enforce_title_validation
        course = SimpleNamespace(course_code="DB101", course_name="Database Systems", description=None)
        for error in (FileNotFoundError(), ValueError("bad artifact"), RuntimeError("initialization")):
            with patch("ml_moderation.validator_v2.models", side_effect=error):
                with self.assertLogs("backend.app.services.title_validation", level="ERROR"):
                    with self.assertRaises(HTTPException) as raised:
                        enforce_title_validation("SQL", course)
                self.assertEqual(raised.exception.status_code, 503)
