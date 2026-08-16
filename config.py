import os

from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(
    BASE_DIR / ".env"
)


# ============================================================
# BOT
# ============================================================

BOT_TOKEN = os.getenv(
    "BOT_TOKEN",
    "",
).strip()


# ============================================================
# ADMIN
# ============================================================

def parse_admin_ids():
    """
    Read ADMIN_IDS from .env.

    Supported formats:

        ADMIN_IDS=123456789
        ADMIN_IDS=123456789,987654321
        ADMIN_IDS=123456789 987654321

    ADMIN_ID is also supported for backwards compatibility.
    """

    values = []

    raw_ids = os.getenv(
        "ADMIN_IDS",
        "",
    ).strip()

    if raw_ids:
        raw_ids = raw_ids.replace(
            ",",
            " ",
        )

        for value in raw_ids.split():
            try:
                values.append(
                    int(value)
                )
            except ValueError:
                pass

    legacy_admin_id = os.getenv(
        "ADMIN_ID",
        "",
    ).strip()

    if legacy_admin_id:
        try:
            values.append(
                int(legacy_admin_id)
            )
        except ValueError:
            pass

    return set(values)


ADMIN_IDS = parse_admin_ids()


# Backwards compatibility.
ADMIN_ID = next(
    iter(ADMIN_IDS),
    None,
)


# ============================================================
# TELEGRAM CHANNEL
# ============================================================

CHANNEL_ID = os.getenv(
    "CHANNEL_ID",
    "",
).strip()


CHANNEL_USERNAME = os.getenv(
    "CHANNEL_USERNAME",
    "",
).strip()


# ============================================================
# BRAVE
# ============================================================

BRAVE_PLAY_STORE_URL = os.getenv(
    "BRAVE_PLAY_STORE_URL",
    "https://play.google.com/store/apps/details?id=com.brave.browser",
).strip()


# ============================================================
# TMDB
# ============================================================

TMDB_API_KEY = os.getenv(
    "TMDB_API_KEY",
    "",
).strip()


TMDB_BASE_URL = os.getenv(
    "TMDB_BASE_URL",
    "https://api.themoviedb.org/3",
).strip().rstrip("/")


TMDB_IMAGE_BASE = os.getenv(
    "TMDB_IMAGE_BASE",
    "https://image.tmdb.org/t/p/w500",
).strip().rstrip("/")


# Optional TMDB Bearer token.
TMDB_BEARER_TOKEN = os.getenv(
    "TMDB_BEARER_TOKEN",
    "",
).strip()


TMDB_HEADERS = {
    "Accept": "application/json",
}


if TMDB_BEARER_TOKEN:
    TMDB_HEADERS["Authorization"] = (
        f"Bearer {TMDB_BEARER_TOKEN}"
    )


# ============================================================
# CRYPTO / SUPPORT WALLETS
# ============================================================

BTC_WALLET = os.getenv(
    "BTC_WALLET",
    "",
).strip()


LTC_WALLET = os.getenv(
    "LTC_WALLET",
    "",
).strip()


BNB_WALLET = os.getenv(
    "BNB_WALLET",
    "",
).strip()


ETH_WALLET = os.getenv(
    "ETH_WALLET",
    "",
).strip()


USDT_WALLET = os.getenv(
    "USDT_WALLET",
    "",
).strip()


DOGE_WALLET = os.getenv(
    "DOGE_WALLET",
    "",
).strip()


TRX_WALLET = os.getenv(
    "TRX_WALLET",
    "",
).strip()


SOL_WALLET = os.getenv(
    "SOL_WALLET",
    "",
).strip()


# ============================================================
# DATABASE
# ============================================================

DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    str(BASE_DIR / "moviebot.db"),
).strip()


# ============================================================
# OPTIONAL BOT SETTINGS
# ============================================================

BOT_NAME = os.getenv(
    "BOT_NAME",
    "MovieBot",
).strip()


# ============================================================
# CONFIGURATION SUMMARY
# ============================================================

def config_summary():
    return {
        "bot_token": bool(BOT_TOKEN),
        "tmdb_api_key": bool(TMDB_API_KEY),
        "admin_ids": sorted(ADMIN_IDS),
        "channel_id": CHANNEL_ID,
        "channel_username": CHANNEL_USERNAME,
        "brave_url": BRAVE_PLAY_STORE_URL,
        "btc_wallet": bool(BTC_WALLET),
        "ltc_wallet": bool(LTC_WALLET),
        "bnb_wallet": bool(BNB_WALLET),
        "eth_wallet": bool(ETH_WALLET),
        "usdt_wallet": bool(USDT_WALLET),
        "doge_wallet": bool(DOGE_WALLET),
        "trx_wallet": bool(TRX_WALLET),
        "sol_wallet": bool(SOL_WALLET),
        "database": DATABASE_PATH,
    }