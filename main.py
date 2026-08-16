import logging

from telegram import Update
from telegram.ext import Application

import database as db
from config import BOT_TOKEN, ADMIN_ID, TMDB_API_KEY
from handlers import user as user_handlers
from handlers import admin as admin_handlers


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


async def error_handler(update: object, context) -> None:
    """Log errors raised by handlers."""
    logger.error(
        "Exception while handling update:",
        exc_info=context.error,
    )


def main():
    # -----------------------------
    # Configuration validation
    # -----------------------------
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is not set. Add BOT_TOKEN to .env"
        )

    if not TMDB_API_KEY:
        raise RuntimeError(
            "TMDB_API_KEY is not set. Add TMDB_API_KEY to .env"
        )

    if not ADMIN_ID:
        logger.warning(
            "No ADMIN_ID configured. "
            "Admin commands will be inaccessible."
        )

    # -----------------------------
    # Database
    # -----------------------------
    db.init_db()

    # -----------------------------
    # Telegram application
    # -----------------------------
    app = Application.builder().token(BOT_TOKEN).build()

    # Store configuration in bot_data
    app.bot_data["admin_id"] = ADMIN_ID

    # -----------------------------
    # Register handlers
    # -----------------------------
    user_handlers.register(app)
    admin_handlers.register(app)

    # -----------------------------
    # Error handler
    # -----------------------------
    app.add_error_handler(error_handler)

    logger.info("================================")
    logger.info("MovieBot starting...")
    logger.info("User handlers loaded.")
    logger.info("Admin handlers loaded.")
    logger.info("TMDB integration enabled.")
    logger.info("================================")

    # -----------------------------
    # Start polling
    # -----------------------------
    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()