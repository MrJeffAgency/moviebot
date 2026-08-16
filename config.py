import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# Telegram
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip()

CHANNEL_USERNAME = (
    os.getenv("CHANNEL_USERNAME", "")
    .strip()
    .lstrip("@")
)

# Admin Telegram numeric ID
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "").strip()

try:
    ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW else 0
except ValueError:
    ADMIN_ID = 0


# Support multiple admins
ADMIN_IDS = {ADMIN_ID} if ADMIN_ID else set()
# ============================================================
# TMDB
# ============================================================

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").strip()

TMDB_BASE_URL = "https://api.themoviedb.org/3"

TMDB_HEADERS = {
    "accept": "application/json",
}

TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


# ============================================================
# Database
# ============================================================

DATABASE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "moviebot.db",
)


# ============================================================
# Brave
# ============================================================

BRAVE_PLAY_STORE_URL = (
    "https://play.google.com/store/apps/details"
    "?id=com.brave.browser"
)


# ============================================================
# Configuration validation
# ============================================================

def validate_config():
    missing = []

    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")

    if not TMDB_API_KEY:
        missing.append("TMDB_API_KEY")

    if not CHANNEL_ID:
        missing.append("CHANNEL_ID")

    if not CHANNEL_USERNAME:
        missing.append("CHANNEL_USERNAME")

    if not ADMIN_ID:
        missing.append("ADMIN_ID")

    if missing:
        raise RuntimeError(
            "Missing configuration values: "
            + ", ".join(missing)
        )