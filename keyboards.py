from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


# ============================================================
# HELPER
# ============================================================

def inline_button(text, callback_data):
    return InlineKeyboardButton(
        text=text,
        callback_data=callback_data,
    )


# ============================================================
# MAIN MENU
# ============================================================

def main_menu():
    return InlineKeyboardMarkup([
        [
            inline_button(
                "🎬 Movies",
                "menu_movie"
            ),
            inline_button(
                "📺 TV Shows",
                "menu_tv"
            ),
        ],
        [
            inline_button(
                "🌟 Popular",
                "menu_popular"
            ),
            inline_button(
                "🏆 Top Rated",
                "menu_toprated"
            ),
        ],
        [
            inline_button(
                "📋 Help",
                "menu_help"
            ),
        ],
    ])


# ============================================================
# MOVIE / TV WATCH BUTTONS
# ============================================================

def movie_keyboard(
    watch_url,
    brave_url=None,
    back_callback=None,
):
    rows = [
        [
            InlineKeyboardButton(
                "▶️ Watch Now",
                url=watch_url,
            )
        ]
    ]

    if brave_url:
        rows.append([
            InlineKeyboardButton(
                "🦁 Open Brave",
                url=brave_url,
            )
        ])

    if back_callback:
        rows.append([
            inline_button(
                "🔙 Back to Seasons",
                back_callback,
            )
        ])

    return InlineKeyboardMarkup(rows)


# ============================================================
# JOIN CHANNEL
# ============================================================

def join_channel_keyboard(channel_username):
    username = channel_username.lstrip("@")

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📢 Join Telegram Channel",
                url=f"https://t.me/{username}",
            )
        ],
        [
            inline_button(
                "✅ Done — Check Membership",
                "check_membership",
            )
        ],
    ])


# ============================================================
# ADMIN HOME
# ============================================================

def admin_home(maintenance=False):
    maintenance_text = (
        "⏹ Maintenance: ON"
        if maintenance
        else "▶️ Maintenance: OFF"
    )

    return InlineKeyboardMarkup([
        [
            inline_button(
                "🎬 Post Movie",
                "admin_post_movie"
            ),
            inline_button(
                "📺 Post TV Show",
                "admin_post_tv"
            ),
        ],
        [
            inline_button(
                "👻 Top 3 Horror",
                "admin_horror"
            ),
        ],
        [
            inline_button(
                "📊 Statistics",
                "admin_stats"
            ),
            inline_button(
                "👥 Recent Users",
                "admin_users"
            ),
        ],
        [
            inline_button(
                maintenance_text,
                "admin_maintenance"
            ),
        ],
        [
            inline_button(
                "⚙️ Channel Settings",
                "admin_channel"
            ),
            inline_button(
                "🆔 Admin ID",
                "admin_id"
            ),
        ],
    ])


# ============================================================
# ADMIN BACK
# ============================================================

def back_admin():
    return InlineKeyboardMarkup([
        [
            inline_button(
                "🔙 Back to Admin Panel",
                "admin_home"
            )
        ]
    ])


# ============================================================
# ADMIN CHANNEL SETTINGS
# ============================================================

def channel_settings_keyboard():
    return InlineKeyboardMarkup([
        [
            inline_button(
                "🔄 Refresh",
                "admin_channel"
            )
        ],
        [
            inline_button(
                "🔙 Back",
                "admin_home"
            )
        ],
    ])


# ============================================================
# ADMIN POST MENU
# ============================================================

def admin_post_menu():
    return InlineKeyboardMarkup([
        [
            inline_button(
                "🎬 Post Movie",
                "admin_post_movie"
            )
        ],
        [
            inline_button(
                "📺 Post TV Show",
                "admin_post_tv"
            )
        ],
        [
            inline_button(
                "🔙 Back",
                "admin_home"
            )
        ],
    ])