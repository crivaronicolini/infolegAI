import os
from dotenv import load_dotenv

load_dotenv()


def require_env(name: str) -> str:
    """Get required environment variable or raise RuntimeError."""
    try:
        return os.environ[name]
    except KeyError as exc:
        raise RuntimeError(f"Missing required environment variable: {name}") from exc


# GCP Configuration
PROJECT_ID = require_env("GCP_PROJECT_ID")
DATASET_NAME = require_env("BQ_DATASET")
TABLE_NAME = require_env("BQ_TABLE")
LOCATION = require_env("GCP_LOCATION")

# Usage Tracking Configuration
USAGE_DB_PATH = require_env("USAGE_DB_PATH")
try:
    USAGE_DAILY_LIMIT = int(require_env("USAGE_DAILY_LIMIT"))
except ValueError:
    raise RuntimeError("USAGE_DAILY_LIMIT must be an integer")

# Debug Configuration
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

