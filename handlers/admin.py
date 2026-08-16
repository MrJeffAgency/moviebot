import html
import requests

from telegram import (
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import database as db
import keyboards as kb

from config import (
    ADMIN_IDS,

    TMDB_API_KEY,
    TMDB_BASE_URL,
    TMDB_HEADERS,
    TMDB_IMAGE_BASE,

    BRAVE_PLAY_STORE_URL,
    CHANNEL_ID,
)


# ============================================================
# ADMIN CHECK
# ============================================================

def admin_only(user_id):
    return user_id in ADMIN_IDS


# ============================================================
# TMDB
# ============================================================

def tmdb_get(
    endpoint,
    params=None,
):
    if not TMDB_API_KEY:
        raise RuntimeError(
            "TMDB_API_KEY is not configured."
        )

    request_params = dict(
        params or {}
    )

    request_params["api_key"] = (
        TMDB_API_KEY
    )

    response = requests.get(
        f"{TMDB_BASE_URL}{endpoint}",
        headers=TMDB_HEADERS,
        params=request_params,
        timeout=15,
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# HELPERS
# ============================================================

def title(item):
    return (
        item.get("title")
        or item.get("name")
        or "Unknown"
    )


def year(item):
    date = (
        item.get("release_date")
        or item.get("first_air_date")
        or ""
    )

    return (
        date[:4]
        if date
        else "N/A"
    )


def poster(item):
    path = item.get(
        "poster_path"
    )

    if not path:
        return None

    return (
        f"{TMDB_IMAGE_BASE}{path}"
    )


def rating(item):
    try:
        return float(
            item.get(
                "vote_average",
                0,
            ) or 0
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0.0


def watch_url(
    item,
    media_type,
):
    item_id = item.get(
        "id"
    )

    if not item_id:
        return None

    if media_type == "tv":
        return (
            f"https://vidsrc.to/embed/tv/"
            f"{item_id}"
        )

    return (
        f"https://vidsrc.to/embed/movie/"
        f"{item_id}"
    )


# ============================================================
# ADMIN HOME
# ============================================================

async def show_admin_panel(
    update,
    context,
):
    maintenance = db.is_maintenance()

    text = (
        "🔐 <b>MovieBot Admin Panel</b>\n\n"
        f"🔧 Maintenance: "
        f"<b>{'ON ⏹' if maintenance else 'OFF ▶️'}</b>\n\n"
        "Choose an option below:"
    )

    markup = kb.admin_home(
        maintenance
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=markup,
        )

    else:
        await update.effective_message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=markup,
        )


# ============================================================
# /ADMIN
# ============================================================

async def admin_command(
    update,
    context,
):
    user = update.effective_user

    if not user or not admin_only(
        user.id
    ):
        await update.effective_message.reply_text(
            "🚫 <b>Access Denied</b>",
            parse_mode="HTML",
        )
        return

    await show_admin_panel(
        update,
        context,
    )


# ============================================================
# MAINTENANCE
# ============================================================

async def maintenance_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    user = update.effective_user

    if not user or not admin_only(
        user.id
    ):
        return

    new_state = not db.is_maintenance()

    db.set_maintenance(
        new_state
    )

    status = (
        "⏹ ON"
        if new_state
        else "▶️ OFF"
    )

    await query.edit_message_text(
        "🔧 <b>Maintenance Mode</b>\n\n"
        f"Status: <b>{status}</b>\n\n"
        + (
            "⚠️ Normal users are now blocked."
            if new_state
            else "✅ Normal users can use the bot."
        ),
        parse_mode="HTML",
        reply_markup=kb.back_admin(),
    )


# ============================================================
# STATISTICS
# ============================================================

async def statistics_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    user = update.effective_user

    if not user or not admin_only(
        user.id
    ):
        return

    users = db.get_user_count()
    searches = db.get_search_count()

    maintenance = (
        "ON ⏹"
        if db.is_maintenance()
        else "OFF ▶️"
    )

    text = (
        "📊 <b>Bot Statistics</b>\n\n"
        f"👥 Total Users: <b>{users}</b>\n"
        f"🔎 Total Searches: <b>{searches}</b>\n"
        f"🔧 Maintenance: <b>{maintenance}</b>"
    )

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.back_admin(),
    )


# ============================================================
# RECENT USERS
# ============================================================

async def recent_users_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    user = update.effective_user

    if not user or not admin_only(
        user.id
    ):
        return

    users = db.get_recent_users(
        15
    )

    if not users:
        text = (
            "👥 <b>Recent Users</b>\n\n"
            "No users registered yet."
        )

    else:
        lines = [
            "👥 <b>Recent Users</b>",
            "",
        ]

        for row in users:
            (
                user_id,
                username,
                first_name,
                last_name,
                joined_at,
                last_seen,
            ) = row

            display_name = (
                first_name
                or username
                or str(user_id)
            )

            if username:
                display_name += (
                    f" @{username}"
                )

            lines.append(
                f"• <b>{html.escape(str(display_name))}</b>\n"
                f"  ID: <code>{user_id}</code>"
            )

        text = "\n".join(
            lines
        )

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.back_admin(),
    )


# ============================================================
# ADMIN ID
# ============================================================

async def admin_id_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    user = update.effective_user

    if not user or not admin_only(
        user.id
    ):
        return

    ids = "\n".join(
        f"• <code>{x}</code>"
        for x in sorted(
            ADMIN_IDS
        )
    )

    if not ids:
        ids = (
            "⚠️ No ADMIN_IDS configured."
        )

    await query.edit_message_text(
        "🆔 <b>Configured Admin IDs</b>\n\n"
        f"{ids}\n\n"
        "Your ID:\n"
        f"<code>{user.id}</code>",
        parse_mode="HTML",
        reply_markup=kb.back_admin(),
    )


# ============================================================
# CHANNEL SETTINGS
# ============================================================

async def channel_settings_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    user = update.effective_user

    if not user or not admin_only(
        user.id
    ):
        return

    configured = db.get_channel_id()

    if not configured:
        configured = CHANNEL_ID

    if not configured:
        configured = "Not configured"

    text = (
        "⚙️ <b>Channel Settings</b>\n\n"
        "Channel ID:\n"
        f"<code>{html.escape(str(configured))}</code>\n\n"
        "The channel ID is normally configured "
        "in your .env file."
    )

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.channel_settings_keyboard(),
    )


# ============================================================
# POST MOVIE MENU
# ============================================================

async def post_movie_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    user = update.effective_user

    if not user or not admin_only(
        user.id
    ):
        return

    context.user_data[
        "admin_post_type"
    ] = "movie"

    await query.edit_message_text(
        "🎬 <b>Post Movie</b>\n\n"
        "Send the movie name now.\n\n"
        "Example:\n"
        "<code>The Batman</code>",
        parse_mode="HTML",
        reply_markup=kb.back_admin(),
    )


# ============================================================
# POST TV MENU
# ============================================================

async def post_tv_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    user = update.effective_user

    if not user or not admin_only(
        user.id
    ):
        return

    context.user_data[
        "admin_post_type"
    ] = "tv"

    await query.edit_message_text(
        "📺 <b>Post TV Show</b>\n\n"
        "Send the TV show name now.\n\n"
        "Example:\n"
        "<code>Breaking Bad</code>",
        parse_mode="HTML",
        reply_markup=kb.back_admin(),
    )


# ============================================================
# ADMIN POST MENU
# ============================================================

async def admin_post_menu_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    user = update.effective_user

    if not user or not admin_only(
        user.id
    ):
        return

    await query.edit_message_text(
        "📢 <b>Post Content</b>\n\n"
        "Choose what you want to post.",
        parse_mode="HTML",
        reply_markup=kb.admin_post_menu(),
    )


# ============================================================
# SEND CHANNEL POST
# ============================================================

async def send_channel_post(
    context,
    item,
    media_type,
):
    channel_id = db.get_channel_id()

    if not channel_id:
        channel_id = CHANNEL_ID

    if not channel_id:
        raise RuntimeError(
            "CHANNEL_ID is not configured."
        )

    item_title = title(
        item
    )

    item_year = year(
        item
    )

    item_rating = rating(
        item
    )

    overview = (
        item.get("overview")
        or "No description available."
    )

    overview = overview.strip()

    if len(overview) > 500:
        overview = (
            overview[:497]
            + "..."
        )

    url = watch_url(
        item,
        media_type,
    )

    if not url:
        raise RuntimeError(
            "Could not create watch URL."
        )

    item_type = (
        "TV Show"
        if media_type == "tv"
        else "Movie"
    )

    caption = (
        f"🎬 <b>{html.escape(item_title)}</b>\n\n"
        f"📺 Type: {item_type}\n"
        f"📅 Year: {html.escape(item_year)}\n"
        f"⭐ Rating: {item_rating:.1f}\n\n"
        f"{html.escape(overview)}\n\n"
        "👇 <b>Click below to watch</b>"
    )

    markup = kb.movie_keyboard(
        url,
        BRAVE_PLAY_STORE_URL,
    )

    image = poster(
        item
    )

    if image:
        await context.bot.send_photo(
            chat_id=channel_id,
            photo=image,
            caption=caption,
            parse_mode="HTML",
            reply_markup=markup,
        )

    else:
        await context.bot.send_message(
            chat_id=channel_id,
            text=caption,
            parse_mode="HTML",
            reply_markup=markup,
        )


# ============================================================
# ADMIN TEXT INPUT
# ============================================================

async def admin_text_handler(
    update,
    context,
):
    user = update.effective_user

    if not user or not admin_only(
        user.id
    ):
        return

    post_type = context.user_data.get(
        "admin_post_type"
    )

    if not post_type:
        return

    search_query = (
        update.effective_message.text
        or ""
    ).strip()

    if not search_query:
        return

    endpoint = (
        "/search/movie"
        if post_type == "movie"
        else "/search/tv"
    )

    try:
        data = tmdb_get(
            endpoint,
            {
                "query": search_query,
                "page": 1,
            },
        )

        results = [
            x
            for x in data.get(
                "results",
                [],
            )
            if x.get("id")
        ][:10]

        if not results:
            await update.effective_message.reply_text(
                "❌ Nothing found. "
                "Try another name."
            )
            return

        context.user_data[
            "admin_results"
        ] = results

        context.user_data[
            "admin_search_type"
        ] = post_type

        keyboard = []

        for item in results:
            item_title = title(
                item
            )

            if len(item_title) > 30:
                item_title = (
                    item_title[:27]
                    + "..."
                )

            keyboard.append([
                kb.inline_button(
                    (
                        f"📌 {item_title} "
                        f"({year(item)})"
                    ),
                    (
                        f"admin_select_"
                        f"{post_type}_"
                        f"{item['id']}"
                    ),
                )
            ])

        keyboard.append([
            kb.inline_button(
                "🔙 Back",
                "admin_home",
            )
        ])

        await update.effective_message.reply_text(
            "🔎 <b>Select what to post:</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
        )

    except Exception as exc:
        await update.effective_message.reply_text(
            "❌ TMDB error:\n"
            f"{html.escape(str(exc))}",
            parse_mode="HTML",
        )


# ============================================================
# SELECT POST
# ============================================================

async def admin_select_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer(
        "Posting..."
    )

    user = update.effective_user

    if not user or not admin_only(
        user.id
    ):
        return

    parts = query.data.split(
        "_"
    )

    if len(parts) != 4:
        return

    media_type = parts[2]

    try:
        item_id = int(
            parts[3]
        )
    except ValueError:
        return

    if media_type not in (
        "movie",
        "tv",
    ):
        return

    try:
        endpoint = (
            f"/movie/{item_id}"
            if media_type == "movie"
            else f"/tv/{item_id}"
        )

        item = tmdb_get(
            endpoint
        )

        await send_channel_post(
            context,
            item,
            media_type,
        )

        context.user_data.pop(
            "admin_post_type",
            None,
        )

        context.user_data.pop(
            "admin_results",
            None,
        )

        await query.edit_message_text(
            "✅ <b>Posted successfully!</b>",
            parse_mode="HTML",
            reply_markup=kb.back_admin(),
        )

    except Exception as exc:
        await query.edit_message_text(
            "❌ <b>Could not post:</b>\n\n"
            f"{html.escape(str(exc))}",
            parse_mode="HTML",
            reply_markup=kb.back_admin(),
        )


# ============================================================
# TOP 3 HORROR
# ============================================================

async def horror_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    user = update.effective_user

    if not user or not admin_only(
        user.id
    ):
        return

    try:
        results = []

        for page in range(
            1,
            4,
        ):
            data = tmdb_get(
                "/discover/tv",
                {
                    "with_genres": "27",
                    "sort_by": "popularity.desc",
                    "vote_count.gte": 20,
                    "page": page,
                },
            )

            results.extend(
                data.get(
                    "results",
                    [],
                )
            )

        results = [
            x
            for x in results
            if x.get("id")
            and x.get("name")
        ]

        unique = {}

        for item in results:
            unique[
                item["id"]
            ] = item

        results = list(
            unique.values()
        )[:3]

        if len(results) < 3:
            fallback = tmdb_get(
                "/tv/popular",
                {
                    "page": 1
                },
            )

            for item in fallback.get(
                "results",
                [],
            ):
                try:
                    item_id = item.get(
                        "id"
                    )

                    if not item_id:
                        continue

                    details = tmdb_get(
                        f"/tv/{item_id}"
                    )

                    genres = [
                        g.get("id")
                        for g in details.get(
                            "genres",
                            [],
                        )
                    ]

                    if 27 in genres:
                        unique[
                            item_id
                        ] = details

                except Exception:
                    continue

                if len(unique) >= 3:
                    break

            results = list(
                unique.values()
            )[:3]

        if not results:
            await query.edit_message_text(
                "❌ No horror shows found right now.",
                reply_markup=kb.back_admin(),
            )
            return

        await query.edit_message_text(
            (
                f"👻 <b>Posting "
                f"{len(results)} Horror Shows...</b>"
            ),
            parse_mode="HTML",
        )

        posted = 0

        for item in results:
            try:
                await send_channel_post(
                    context,
                    item,
                    "tv",
                )

                posted += 1

            except Exception:
                continue

        await context.bot.send_message(
            chat_id=user.id,
            text=(
                f"✅ <b>{posted} horror "
                f"shows posted successfully!</b>"
            ),
            parse_mode="HTML",
            reply_markup=kb.back_admin(),
        )

    except Exception as exc:
        await query.message.reply_text(
            "❌ Horror error:\n"
            f"{html.escape(str(exc))}",
            parse_mode="HTML",
            reply_markup=kb.back_admin(),
        )


# ============================================================
# ADMIN HOME CALLBACK
# ============================================================

async def admin_home_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    user = update.effective_user

    if not user or not admin_only(
        user.id
    ):
        return

    context.user_data.pop(
        "admin_post_type",
        None,
    )

    await show_admin_panel(
        update,
        context,
    )


# ============================================================
# REGISTER ADMIN HANDLERS
# ============================================================

def register(
    app: Application,
):

    # --------------------------------------------------------
    # /admin
    # --------------------------------------------------------

    app.add_handler(
        CommandHandler(
            "admin",
            admin_command,
        )
    )

    # --------------------------------------------------------
    # Admin text input
    # --------------------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            admin_text_handler,
        )
    )

    # --------------------------------------------------------
    # Admin home
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            admin_home_callback,
            pattern=r"^admin_home$",
        )
    )

    # --------------------------------------------------------
    # Maintenance
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            maintenance_callback,
            pattern=r"^admin_maintenance$",
        )
    )

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            statistics_callback,
            pattern=r"^admin_stats$",
        )
    )

    # --------------------------------------------------------
    # Recent users
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            recent_users_callback,
            pattern=r"^admin_users$",
        )
    )

    # --------------------------------------------------------
    # Admin ID
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            admin_id_callback,
            pattern=r"^admin_id$",
        )
    )

    # --------------------------------------------------------
    # Channel settings
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            channel_settings_callback,
            pattern=r"^admin_channel$",
        )
    )

    # --------------------------------------------------------
    # Post movie
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            post_movie_callback,
            pattern=r"^admin_post_movie$",
        )
    )

    # --------------------------------------------------------
    # Post TV
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            post_tv_callback,
            pattern=r"^admin_post_tv$",
        )
    )

    # --------------------------------------------------------
    # Post menu
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            admin_post_menu_callback,
            pattern=r"^admin_post_menu$",
        )
    )

    # --------------------------------------------------------
    # Top 3 horror
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            horror_callback,
            pattern=r"^admin_horror$",
        )
    )

    # --------------------------------------------------------
    # Selected movie / TV
    #
    # THIS IS THE FINAL ADMIN CALLBACK REGISTRATION.
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            admin_select_callback,
            pattern=r"^admin_select_(movie|tv)_\d+$",
        )
    )