"""Configuration constants for ML filename moderation."""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
DATASETS_DIR = PACKAGE_DIR / "datasets"
SOURCES_DIR = DATASETS_DIR / "sources"
GENERATED_DIR = DATASETS_DIR / "generated"
MODELS_DIR = PACKAGE_DIR / "models"
REPORTS_DIR = PACKAGE_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

DEFAULT_MODEL_PATH = MODELS_DIR / "filename_moderator.joblib"
PROFANITY_WORDS_PATH = DATASETS_DIR / "profanity_words.csv"
CLEAN_FILENAMES_PATH = DATASETS_DIR / "clean_filenames.csv"

MODEL_VERSION = "1.0.0"
RANDOM_SEED = 42

# Maximum input length accepted by the normalizer to prevent DoS on huge strings.
MAX_INPUT_LENGTH = 512

# User-facing rejection message matching backend error conventions.
REJECTION_MESSAGE = "Please choose an appropriate name for your study material."
UNAVAILABLE_MESSAGE = "Filename moderation service is temporarily unavailable."

# Default threshold placeholder; production artifacts store their validation-tuned threshold.
DEFAULT_THRESHOLD = 0.50
DEFAULT_UNCERTAIN_LOW = 0.40
DEFAULT_UNCERTAIN_HIGH = 0.65
