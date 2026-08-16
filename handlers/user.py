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
)

import database as db
import keyboards as kb

from config import (
    ADMIN_IDS,
    CHANNEL_USERNAME,

    TMDB_API_KEY,
    TMDB_BASE_URL,
    TMDB_HEADERS,
    TMDB_IMAGE_BASE,

    BRAVE_PLAY_STORE_URL,
    CHANNEL_ID,

    BTC_WALLET,
    LTC_WALLET,
    BNB_WALLET,
    ETH_WALLET,
    USDT_WALLET,
    DOGE_WALLET,
    TRX_WALLET,
    SOL_WALLET,
)


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

def get_title(item):
    return (
        item.get("title")
        or item.get("name")
        or "Unknown"
    )


def get_year(item):
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


def get_rating(item):
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


def get_poster_url(item):
    path = item.get(
        "poster_path"
    )

    if not path:
        return None

    return (
        f"{TMDB_IMAGE_BASE}{path}"
    )


def get_item_type(item):
    media_type = item.get(
        "media_type"
    )

    if media_type == "tv":
        return "TV Show"

    if media_type == "movie":
        return "Movie"

    if item.get("first_air_date"):
        return "TV Show"

    return "Movie"


def get_vidsrc_url(item):
    item_id = item.get("id")

    if not item_id:
        return None

    if get_item_type(item) == "TV Show":
        return (
            f"https://vidsrc.to/embed/tv/"
            f"{item_id}"
        )

    return (
        f"https://vidsrc.to/embed/movie/"
        f"{item_id}"
    )


def clean_overview(
    overview,
    maximum=500,
):
    overview = (
        overview
        or "No description available."
    ).strip()

    if len(overview) > maximum:
        overview = (
            overview[: maximum - 3]
            + "..."
        )

    return overview


# ============================================================
# ADMIN CHECK
# ============================================================

def is_admin(user_id):
    return user_id in ADMIN_IDS


# ============================================================
# MAINTENANCE
# ============================================================

async def maintenance_guard(
    update,
):
    user = update.effective_user

    if not user:
        return False

    if is_admin(user.id):
        return False

    if db.is_maintenance():
        message = (
            update.effective_message
        )

        if message:
            await message.reply_text(
                "🔧 <b>Bot Maintenance</b>\n\n"
                "The bot is temporarily under "
                "maintenance.\n\n"
                "Please try again later. 🛠️",
                parse_mode="HTML",
            )

        return True

    return False


# ============================================================
# CHANNEL MEMBERSHIP
# ============================================================

async def check_user_membership(
    update,
    context,
):
    user = update.effective_user

    if not user:
        return False

    if is_admin(user.id):
        return True

    if not CHANNEL_USERNAME:
        return True

    try:
        member = (
            await context.bot.get_chat_member(
                f"@{CHANNEL_USERNAME.lstrip('@')}",
                user.id,
            )
        )

        if member.status in (
            "member",
            "administrator",
            "creator",
        ):
            return True

    except Exception:
        pass

    message = (
        update.effective_message
    )

    if message:
        await message.reply_text(
            "🔐 <b>Join our Telegram channel first</b>\n\n"
            "Join the channel and then press "
            "<b>Done — Check Membership</b>.",
            parse_mode="HTML",
            reply_markup=kb.join_channel_keyboard(
                CHANNEL_USERNAME
            ),
        )

    return False


# ============================================================
# COMMON ACCESS
# ============================================================

async def user_access_allowed(
    update,
    context,
):
    if await maintenance_guard(
        update
    ):
        return False

    if not await check_user_membership(
        update,
        context,
    ):
        return False

    return True


# ============================================================
# SEND MOVIE / TV
# ============================================================

async def send_post_with_buttons(
    update,
    context,
    item,
    is_channel=False,
    back_callback=None,
):
    title = get_title(item)
    item_year = get_year(item)
    item_type = get_item_type(item)
    rating = get_rating(item)

    overview = clean_overview(
        item.get("overview")
    )

    watch_url = get_vidsrc_url(
        item
    )

    poster_url = get_poster_url(
        item
    )

    if not watch_url:
        raise RuntimeError(
            "Could not create playback URL."
        )

    caption = (
        f"🎬 <b>{html.escape(title)}</b>\n\n"
        f"📺 Type: {html.escape(item_type)}\n"
        f"📅 Year: {html.escape(item_year)}\n"
        f"⭐ Rating: {rating:.1f}\n\n"
        f"{html.escape(overview)}\n\n"
        "👇 <b>Click below to watch</b>\n"
        "🦁 Best experienced with Brave Browser."
    )

    markup = kb.movie_keyboard(
        watch_url=watch_url,
        brave_url=BRAVE_PLAY_STORE_URL,
        back_callback=back_callback,
    )

    if is_channel:
        channel_id = (
            db.get_channel_id()
        )

        if not channel_id:
            channel_id = CHANNEL_ID

        if not channel_id:
            raise RuntimeError(
                "CHANNEL_ID is not configured."
            )

        chat_id = channel_id

    else:
        chat_id = (
            update.effective_chat.id
        )

    if poster_url:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=poster_url,
            caption=caption,
            parse_mode="HTML",
            reply_markup=markup,
        )

    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=caption,
            parse_mode="HTML",
            reply_markup=markup,
        )


# ============================================================
# START
# ============================================================

async def start(
    update,
    context,
):
    user = update.effective_user

    if user:
        db.save_user(
            user.id,
            user.username,
            user.first_name,
            user.last_name,
        )

    if await maintenance_guard(
        update
    ):
        return

    if not await check_user_membership(
        update,
        context,
    ):
        return

    await update.effective_message.reply_text(
        "🎬 <b>Welcome to MovieBot!</b>\n\n"
        "Search for movies and TV shows.\n\n"
        "🎬 <code>/movie Batman</code>\n"
        "📺 <code>/tvshow Breaking Bad</code>\n"
        "📺 <code>/seasons Breaking Bad</code>\n"
        "🌟 <code>/popular</code>\n"
        "🏆 <code>/toprated</code>\n"
        "📋 <code>/help</code>\n\n"
        "❤️ <b>Support</b> is available from "
        "the main menu.",
        parse_mode="HTML",
        reply_markup=kb.main_menu(),
    )


# ============================================================
# HELP
# ============================================================

async def help_cmd(
    update,
    context,
):
    if not await user_access_allowed(
        update,
        context,
    ):
        return

    await update.effective_message.reply_text(
        "📋 <b>MovieBot Commands</b>\n\n"
        "🎬 <code>/movie Batman</code>\n"
        "Search movies.\n\n"
        "📺 <code>/tvshow Breaking Bad</code>\n"
        "Search TV shows.\n\n"
        "📺 <code>/seasons Breaking Bad</code>\n"
        "Choose a TV show and view seasons.\n\n"
        "🌟 <code>/popular</code>\n"
        "Show popular movies.\n\n"
        "🏆 <code>/toprated</code>\n"
        "Show top-rated movies.\n\n"
        "❤️ <b>Support</b>\n"
        "Open the Support button from the main menu.",
        parse_mode="HTML",
    )


# ============================================================
# SEARCH RESULT TEXT
# ============================================================

def build_results_text(
    results,
    query,
    media_type,
    page=0,
    per_page=10,
):
    start = page * per_page

    end = min(
        start + per_page,
        len(results),
    )

    heading = (
        "🎬 Movie Results"
        if media_type == "movie"
        else "📺 TV Show Results"
    )

    lines = [
        f"<b>{heading}</b>",
        "",
        f"🔎 <b>{html.escape(query)}</b>",
        "",
        "👇 Choose a title:",
        "",
    ]

    for index, item in enumerate(
        results[start:end],
        start=start + 1,
    ):
        item_title = html.escape(
            get_title(item)
        )

        item_year = get_year(
            item
        )

        rating = get_rating(
            item
        )

        lines.append(
            f"<b>{index}.</b> "
            f"{item_title} "
            f"({item_year}) "
            f"⭐ {rating:.1f}"
        )

    if start < end:
        showing = (
            f"Showing {start + 1}-{end} "
            f"of {len(results)} results."
        )
    else:
        showing = (
            f"No results on page "
            f"{page + 1}."
        )

    lines.extend([
        "",
        showing,
    ])

    return "\n".join(lines)


# ============================================================
# SEARCH KEYBOARD
# ============================================================

def build_search_keyboard(
    results,
    media_type,
    page=0,
    per_page=10,
):
    start = page * per_page
    end = start + per_page

    keyboard = []

    for index, item in enumerate(
        results[start:end],
        start=start + 1,
    ):
        item_title = get_title(
            item
        )

        if len(item_title) > 30:
            item_title = (
                item_title[:27]
                + "..."
            )

        item_year = get_year(
            item
        )

        text = (
            f"{index}. {item_title}"
        )

        if item_year != "N/A":
            text += (
                f" ({item_year})"
            )

        item_id = item.get(
            "id"
        )

        if not item_id:
            continue

        keyboard.append([
            kb.inline_button(
                text,
                (
                    f"select_"
                    f"{media_type}_"
                    f"{item_id}"
                ),
            )
        ])

    navigation = []

    if page > 0:
        navigation.append(
            kb.inline_button(
                "⬅️ Previous",
                (
                    f"results_"
                    f"{media_type}_"
                    f"{page - 1}"
                ),
            )
        )

    if end < len(results):
        navigation.append(
            kb.inline_button(
                "Next ➡️",
                (
                    f"results_"
                    f"{media_type}_"
                    f"{page + 1}"
                ),
            )
        )

    if navigation:
        keyboard.append(
            navigation
        )

    keyboard.append([
        kb.inline_button(
            "❌ Cancel",
            "results_cancel",
        )
    ])

    return InlineKeyboardMarkup(
        keyboard
    )


def store_results(
    context,
    results,
    search_query,
    media_type,
):
    context.user_data[
        "search_results"
    ] = results

    context.user_data[
        "search_query"
    ] = search_query

    context.user_data[
        "search_media_type"
    ] = media_type


# ============================================================
# MOVIE SEARCH
# ============================================================

async def movie_search_cmd(
    update,
    context,
):
    if not await user_access_allowed(
        update,
        context,
    ):
        return

    if not context.args:
        await update.effective_message.reply_text(
            "❌ Usage:\n"
            "<code>/movie Batman</code>",
            parse_mode="HTML",
        )
        return

    search_query = " ".join(
        context.args
    )

    try:
        data = tmdb_get(
            "/search/movie",
            {
                "query": search_query,
                "page": 1,
                "include_adult": "false",
            },
        )

        results = [
            x
            for x in data.get(
                "results",
                [],
            )
            if x.get("id")
        ][:20]

        if not results:
            await update.effective_message.reply_text(
                "❌ No movies found."
            )
            return

        store_results(
            context,
            results,
            search_query,
            "movie",
        )

        await update.effective_message.reply_text(
            build_results_text(
                results,
                search_query,
                "movie",
            ),
            parse_mode="HTML",
            reply_markup=build_search_keyboard(
                results,
                "movie",
            ),
        )

        user = update.effective_user

        if user:
            db.save_search(
                user.id,
                search_query,
                "movie",
            )

    except Exception as exc:
        await update.effective_message.reply_text(
            "❌ TMDB error:\n"
            f"<code>{html.escape(str(exc))}</code>",
            parse_mode="HTML",
        )


# ============================================================
# TV SEARCH
# ============================================================

async def tvshow_search_cmd(
    update,
    context,
):
    if not await user_access_allowed(
        update,
        context,
    ):
        return

    if not context.args:
        await update.effective_message.reply_text(
            "❌ Usage:\n"
            "<code>/tvshow Breaking Bad</code>",
            parse_mode="HTML",
        )
        return

    search_query = " ".join(
        context.args
    )

    try:
        data = tmdb_get(
            "/search/tv",
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
        ][:20]

        if not results:
            await update.effective_message.reply_text(
                "❌ No TV shows found."
            )
            return

        store_results(
            context,
            results,
            search_query,
            "tv",
        )

        await update.effective_message.reply_text(
            build_results_text(
                results,
                search_query,
                "tv",
            ),
            parse_mode="HTML",
            reply_markup=build_search_keyboard(
                results,
                "tv",
            ),
        )

        user = update.effective_user

        if user:
            db.save_search(
                user.id,
                search_query,
                "tv",
            )

    except Exception as exc:
        await update.effective_message.reply_text(
            "❌ TMDB error:\n"
            f"<code>{html.escape(str(exc))}</code>",
            parse_mode="HTML",
        )


# ============================================================
# SELECT MOVIE / TV
# ============================================================

async def select_result_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    parts = query.data.split(
        "_"
    )

    if len(parts) != 3:
        return

    _, media_type, item_id_text = parts

    try:
        item_id = int(
            item_id_text
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

        item["media_type"] = (
            media_type
        )

        await query.edit_message_text(
            "⏳ Loading..."
        )

        if media_type == "tv":
            context.user_data[
                "selected_tv_id"
            ] = item_id

        await send_post_with_buttons(
            update,
            context,
            item,
        )

    except Exception as exc:
        await query.message.reply_text(
            "❌ TMDB error:\n"
            f"{html.escape(str(exc))}",
            parse_mode="HTML",
        )


# ============================================================
# PAGINATION
# ============================================================

async def results_page_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    parts = query.data.split(
        "_"
    )

    if len(parts) != 3:
        return

    _, media_type, page_text = parts

    try:
        page = int(
            page_text
        )
    except ValueError:
        return

    results = context.user_data.get(
        "search_results",
        [],
    )

    search_query = context.user_data.get(
        "search_query",
        "",
    )

    if not results:
        await query.edit_message_text(
            "⚠️ Search expired. "
            "Please search again."
        )
        return

    await query.edit_message_text(
        build_results_text(
            results,
            search_query,
            media_type,
            page,
        ),
        parse_mode="HTML",
        reply_markup=build_search_keyboard(
            results,
            media_type,
            page,
        ),
    )


# ============================================================
# CANCEL
# ============================================================

async def results_cancel_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    context.user_data.pop(
        "search_results",
        None,
    )

    context.user_data.pop(
        "search_query",
        None,
    )

    context.user_data.pop(
        "search_media_type",
        None,
    )

    await query.edit_message_text(
        "❌ Search cancelled."
    )


# ============================================================
# SEASONS SEARCH
# ============================================================

async def seasons_cmd(
    update,
    context,
):
    if not await user_access_allowed(
        update,
        context,
    ):
        return

    if not context.args:
        await update.effective_message.reply_text(
            "❌ Usage:\n"
            "<code>/seasons Breaking Bad</code>",
            parse_mode="HTML",
        )
        return

    search_query = " ".join(
        context.args
    )

    try:
        data = tmdb_get(
            "/search/tv",
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
        ][:20]

        if not results:
            await update.effective_message.reply_text(
                "❌ No TV shows found."
            )
            return

        context.user_data[
            "season_results"
        ] = results

        keyboard = []

        for item in results:
            item_title = get_title(
                item
            )

            item_year = get_year(
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
                        f"📺 {item_title} "
                        f"({item_year})"
                    ),
                    (
                        f"season_show_"
                        f"{item['id']}"
                    ),
                )
            ])

        keyboard.append([
            kb.inline_button(
                "❌ Cancel",
                "results_cancel",
            )
        ])

        await update.effective_message.reply_text(
            "📺 <b>Choose a TV Show</b>\n\n"
            f"Search: <b>{html.escape(search_query)}</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
        )

    except Exception as exc:
        await update.effective_message.reply_text(
            "❌ TMDB error:\n"
            f"<code>{html.escape(str(exc))}</code>",
            parse_mode="HTML",
        )


# ============================================================
# SHOW SEASONS
# ============================================================

async def season_show_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    try:
        show_id = int(
            query.data.split("_")[-1]
        )
    except ValueError:
        return

    try:
        details = tmdb_get(
            f"/tv/{show_id}"
        )

        seasons = [
            s
            for s in details.get(
                "seasons",
                [],
            )
            if s.get(
                "season_number"
            ) != 0
        ]

        if not seasons:
            await query.message.reply_text(
                "❌ No seasons found."
            )
            return

        context.user_data[
            "current_tv_id"
        ] = show_id

        context.user_data[
            "current_tv_name"
        ] = details.get(
            "name",
            "TV Show",
        )

        keyboard = []

        for season in seasons:
            number = season.get(
                "season_number"
            )

            episodes = season.get(
                "episode_count",
                0,
            )

            keyboard.append([
                kb.inline_button(
                    (
                        f"📀 Season {number} "
                        f"({episodes} episodes)"
                    ),
                    (
                        f"season_"
                        f"{show_id}_"
                        f"{number}"
                    ),
                )
            ])

        keyboard.append([
            kb.inline_button(
                "🔙 Back to TV Results",
                "seasons_back",
            )
        ])

        await query.edit_message_text(
            (
                f"📺 <b>"
                f"{html.escape(details.get('name', 'TV Show'))}"
                f"</b>\n\n"
                "Choose a season:"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
        )

    except Exception as exc:
        await query.message.reply_text(
            "❌ TMDB error:\n"
            f"{html.escape(str(exc))}",
            parse_mode="HTML",
        )


# ============================================================
# EPISODES
# ============================================================

async def season_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    parts = query.data.split(
        "_"
    )

    if len(parts) != 3:
        return

    try:
        show_id = int(
            parts[1]
        )

        season_number = int(
            parts[2]
        )

    except ValueError:
        return

    try:
        data = tmdb_get(
            f"/tv/{show_id}/season/"
            f"{season_number}"
        )

        episodes = data.get(
            "episodes",
            [],
        )

        if not episodes:
            await query.message.reply_text(
                "❌ No episodes found."
            )
            return

        context.user_data[
            "current_tv_id"
        ] = show_id

        context.user_data[
            "current_season"
        ] = season_number

        keyboard = []

        for episode in episodes:
            episode_number = episode.get(
                "episode_number"
            )

            name = episode.get(
                "name",
                "Episode",
            )

            if len(name) > 35:
                name = (
                    name[:32]
                    + "..."
                )

            keyboard.append([
                kb.inline_button(
                    (
                        f"▶️ {episode_number}. "
                        f"{name}"
                    ),
                    (
                        f"episode_"
                        f"{show_id}_"
                        f"{season_number}_"
                        f"{episode_number}"
                    ),
                )
            ])

        keyboard.append([
            kb.inline_button(
                "🔙 Back to Seasons",
                (
                    f"back_seasons_"
                    f"{show_id}"
                ),
            )
        ])

        await query.edit_message_text(
            (
                f"📺 <b>Season "
                f"{season_number}</b>\n\n"
                "Choose an episode:"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
        )

    except Exception as exc:
        await query.message.reply_text(
            "❌ TMDB error:\n"
            f"{html.escape(str(exc))}",
            parse_mode="HTML",
        )


# ============================================================
# EPISODE WATCH
# ============================================================

async def episode_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    parts = query.data.split(
        "_"
    )

    if len(parts) != 4:
        return

    try:
        show_id = int(
            parts[1]
        )

        season_number = int(
            parts[2]
        )

        episode_number = int(
            parts[3]
        )

    except ValueError:
        return

    watch_url = (
        f"https://vidsrc.to/embed/tv/"
        f"{show_id}/"
        f"{season_number}-"
        f"{episode_number}"
    )

    markup = kb.movie_keyboard(
        watch_url,
        BRAVE_PLAY_STORE_URL,
        (
            f"back_episodes_"
            f"{show_id}_"
            f"{season_number}"
        ),
    )

    await query.edit_message_text(
        "🎬 <b>Episode Ready</b>\n\n"
        f"📺 Season {season_number}\n"
        f"🎞 Episode {episode_number}\n\n"
        "👇 Click below to watch.",
        parse_mode="HTML",
        reply_markup=markup,
    )


# ============================================================
# BACK TO EPISODES
# ============================================================

async def back_episodes_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    parts = query.data.split(
        "_"
    )

    if len(parts) != 3:
        return

    try:
        show_id = int(
            parts[1]
        )

        season_number = int(
            parts[2]
        )

    except ValueError:
        return

    try:
        data = tmdb_get(
            f"/tv/{show_id}/season/"
            f"{season_number}"
        )

        episodes = data.get(
            "episodes",
            [],
        )

        if not episodes:
            await query.edit_message_text(
                "❌ No episodes found."
            )
            return

        keyboard = []

        for episode in episodes:
            episode_number = episode.get(
                "episode_number"
            )

            name = episode.get(
                "name",
                "Episode",
            )

            if len(name) > 35:
                name = (
                    name[:32]
                    + "..."
                )

            keyboard.append([
                kb.inline_button(
                    (
                        f"▶️ {episode_number}. "
                        f"{name}"
                    ),
                    (
                        f"episode_"
                        f"{show_id}_"
                        f"{season_number}_"
                        f"{episode_number}"
                    ),
                )
            ])

        keyboard.append([
            kb.inline_button(
                "🔙 Back to Seasons",
                f"back_seasons_{show_id}",
            )
        ])

        await query.edit_message_text(
            (
                f"📺 <b>Season "
                f"{season_number}</b>\n\n"
                "Choose an episode:"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
        )

    except Exception as exc:
        await query.edit_message_text(
            "❌ TMDB error:\n"
            f"<code>{html.escape(str(exc))}</code>",
            parse_mode="HTML",
        )


# ============================================================
# BACK TO SEASONS
# ============================================================

async def back_seasons_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    try:
        show_id = int(
            query.data.split("_")[-1]
        )
    except ValueError:
        return

    try:
        details = tmdb_get(
            f"/tv/{show_id}"
        )

        seasons = [
            s
            for s in details.get(
                "seasons",
                [],
            )
            if s.get(
                "season_number"
            ) != 0
        ]

        keyboard = []

        for season in seasons:
            number = season.get(
                "season_number"
            )

            episodes = season.get(
                "episode_count",
                0,
            )

            keyboard.append([
                kb.inline_button(
                    (
                        f"📀 Season {number} "
                        f"({episodes} episodes)"
                    ),
                    (
                        f"season_"
                        f"{show_id}_"
                        f"{number}"
                    ),
                )
            ])

        await query.edit_message_text(
            (
                f"📺 <b>"
                f"{html.escape(details.get('name', 'TV Show'))}"
                f"</b>\n\n"
                "Choose a season:"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
        )

    except Exception as exc:
        await query.message.reply_text(
            f"❌ {html.escape(str(exc))}",
            parse_mode="HTML",
        )


# ============================================================
# SEASONS BACK
# ============================================================

async def seasons_back_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    results = context.user_data.get(
        "season_results",
        [],
    )

    if not results:
        await query.edit_message_text(
            "⚠️ Previous search expired. "
            "Please use /seasons again."
        )
        return

    keyboard = []

    for item in results:
        item_title = get_title(
            item
        )

        item_year = get_year(
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
                    f"📺 {item_title} "
                    f"({item_year})"
                ),
                (
                    f"season_show_"
                    f"{item['id']}"
                ),
            )
        ])

    keyboard.append([
        kb.inline_button(
            "❌ Cancel",
            "results_cancel",
        )
    ])

    await query.edit_message_text(
        "📺 <b>Choose a TV Show</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
    )


# ============================================================
# POPULAR
# ============================================================

async def popular_cmd(
    update,
    context,
):
    if not await user_access_allowed(
        update,
        context,
    ):
        return

    try:
        data = tmdb_get(
            "/movie/popular",
            {
                "page": 1
            },
        )

        movies = data.get(
            "results",
            [],
        )

        if not movies:
            await update.effective_message.reply_text(
                "❌ No popular movies found."
            )
            return

        item = movies[0]
        item["media_type"] = "movie"

        await send_post_with_buttons(
            update,
            context,
            item,
        )

    except Exception as exc:
        await update.effective_message.reply_text(
            "❌ TMDB error:\n"
            f"<code>{html.escape(str(exc))}</code>",
            parse_mode="HTML",
        )


# ============================================================
# TOP RATED
# ============================================================

async def toprated_cmd(
    update,
    context,
):
    if not await user_access_allowed(
        update,
        context,
    ):
        return

    try:
        data = tmdb_get(
            "/movie/top_rated",
            {
                "page": 1
            },
        )

        movies = data.get(
            "results",
            [],
        )

        if not movies:
            await update.effective_message.reply_text(
                "❌ No top-rated movies found."
            )
            return

        item = movies[0]
        item["media_type"] = "movie"

        await send_post_with_buttons(
            update,
            context,
            item,
        )

    except Exception as exc:
        await update.effective_message.reply_text(
            "❌ TMDB error:\n"
            f"<code>{html.escape(str(exc))}</code>",
            parse_mode="HTML",
        )


# ============================================================
# MEMBERSHIP CHECK
# ============================================================

async def membership_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    user = update.effective_user

    if not user:
        return

    if not CHANNEL_USERNAME:
        await query.message.reply_text(
            "⚠️ Channel membership is not configured."
        )
        return

    try:
        member = (
            await context.bot.get_chat_member(
                f"@{CHANNEL_USERNAME.lstrip('@')}",
                user.id,
            )
        )

        if member.status in (
            "member",
            "administrator",
            "creator",
        ):
            db.save_user(
                user.id,
                user.username,
                user.first_name,
                user.last_name,
            )

            await query.message.reply_text(
                "✅ <b>Membership verified!</b>\n\n"
                "🎬 Welcome to MovieBot.",
                parse_mode="HTML",
                reply_markup=kb.main_menu(),
            )

        else:
            await query.message.reply_text(
                "❌ <b>You are not a member yet.</b>\n\n"
                "Join the channel first and "
                "press the button again.",
                parse_mode="HTML",
                reply_markup=kb.join_channel_keyboard(
                    CHANNEL_USERNAME
                ),
            )

    except Exception:
        await query.message.reply_text(
            "⚠️ I couldn't verify membership.\n\n"
            "Make sure the bot is an administrator "
            "of the Telegram channel.",
            parse_mode="HTML",
            reply_markup=kb.join_channel_keyboard(
                CHANNEL_USERNAME
            ),
        )


# ============================================================
# MAIN MENU
# ============================================================

async def menu_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    if await maintenance_guard(
        update
    ):
        return

    action = query.data

    if action == "menu_movie":
        await query.message.reply_text(
            "🎬 <b>Movie Search</b>\n\n"
            "Send:\n"
            "<code>/movie Movie Name</code>",
            parse_mode="HTML",
        )

    elif action == "menu_tv":
        await query.message.reply_text(
            "📺 <b>TV Show Search</b>\n\n"
            "Send:\n"
            "<code>/tvshow TV Show Name</code>",
            parse_mode="HTML",
        )

    elif action == "menu_popular":
        await popular_cmd(
            update,
            context,
        )

    elif action == "menu_toprated":
        await toprated_cmd(
            update,
            context,
        )

    elif action == "menu_help":
        await help_cmd(
            update,
            context,
        )


# ============================================================
# SUPPORT / DONATION
# ============================================================

SUPPORT_WALLETS = {
    "btc": (
        "₿ Bitcoin",
        BTC_WALLET,
    ),

    "ltc": (
        "Ł Litecoin",
        LTC_WALLET,
    ),

    "bnb": (
        "🟡 BNB",
        BNB_WALLET,
    ),

    "eth": (
        "♦️ Ethereum",
        ETH_WALLET,
    ),

    "usdt": (
        "💵 USDT",
        USDT_WALLET,
    ),

    "doge": (
        "🐕 Dogecoin",
        DOGE_WALLET,
    ),

    "trx": (
        "🔺 TRON",
        TRX_WALLET,
    ),

    "sol": (
        "☀️ Solana",
        SOL_WALLET,
    ),
}


async def support_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    if await maintenance_guard(
        update
    ):
        return

    action = query.data

    # --------------------------------------------------------
    # MAIN SUPPORT SCREEN
    # --------------------------------------------------------

    if action == "support":
        await query.message.reply_text(
            "❤️ <b>Support MovieBot</b>\n\n"
            "Thank you for supporting the bot! 🙏\n\n"
            "If you enjoy using MovieBot and "
            "would like to support the admin, "
            "you can donate using one of "
            "the wallets below.\n\n"
            "💰 <b>Choose your cryptocurrency:</b>",
            parse_mode="HTML",
            reply_markup=kb.support_keyboard(),
        )
        return

    # --------------------------------------------------------
    # BACK TO MAIN MENU
    # --------------------------------------------------------

    if action == "support_back":
        await query.message.reply_text(
            "🏠 <b>Main Menu</b>",
            parse_mode="HTML",
            reply_markup=kb.main_menu(),
        )
        return

    # --------------------------------------------------------
    # WALLET
    # --------------------------------------------------------

    if not action.startswith(
        "support_"
    ):
        return

    coin = action.replace(
        "support_",
        "",
        1,
    )

    wallet_data = (
        SUPPORT_WALLETS.get(
            coin
        )
    )

    if not wallet_data:
        await query.message.reply_text(
            "❌ Unknown cryptocurrency.",
            reply_markup=kb.support_keyboard(),
        )
        return

    coin_name, wallet = wallet_data

    if not wallet:
        await query.message.reply_text(
            f"⚠️ <b>{html.escape(coin_name)}</b>\n\n"
            "The admin has not configured a "
            "wallet address for this cryptocurrency yet.\n\n"
            "Please choose another option.",
            parse_mode="HTML",
            reply_markup=kb.support_keyboard(),
        )
        return

    await query.message.reply_text(
        "🙏 <b>Thank you for supporting MovieBot!</b>\n\n"
        f"💰 <b>{html.escape(coin_name)}</b>\n\n"
        "📋 <b>Wallet Address</b>\n"
        f"<code>{html.escape(wallet)}</code>\n\n"
        "👆 Tap the wallet address above to copy it.\n\n"
        "❤️ Every contribution helps keep "
        "the bot running. Thank you!",
        parse_mode="HTML",
        reply_markup=kb.support_keyboard(),
    )


# ============================================================
# REGISTER USER HANDLERS
# ============================================================

def register(
    app: Application,
):

    # --------------------------------------------------------
    # Commands
    # --------------------------------------------------------

    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(
        CommandHandler(
            "help",
            help_cmd,
        )
    )

    app.add_handler(
        CommandHandler(
            "movie",
            movie_search_cmd,
        )
    )

    app.add_handler(
        CommandHandler(
            "tvshow",
            tvshow_search_cmd,
        )
    )

    app.add_handler(
        CommandHandler(
            "seasons",
            seasons_cmd,
        )
    )

    app.add_handler(
        CommandHandler(
            "popular",
            popular_cmd,
        )
    )

    app.add_handler(
        CommandHandler(
            "toprated",
            toprated_cmd,
        )
    )

    # --------------------------------------------------------
    # Membership
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            membership_callback,
            pattern=r"^check_membership$",
        )
    )

    # --------------------------------------------------------
    # Movie / TV selection
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            select_result_callback,
            pattern=r"^select_(movie|tv)_\d+$",
        )
    )

    # --------------------------------------------------------
    # Search pagination
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            results_page_callback,
            pattern=r"^results_(movie|tv)_\d+$",
        )
    )

    # --------------------------------------------------------
    # Search cancel
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            results_cancel_callback,
            pattern=r"^results_cancel$",
        )
    )

    # --------------------------------------------------------
    # TV seasons search
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            season_show_callback,
            pattern=r"^season_show_\d+$",
        )
    )

    # --------------------------------------------------------
    # Seasons back
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            seasons_back_callback,
            pattern=r"^seasons_back$",
        )
    )

    # --------------------------------------------------------
    # Season selection
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            season_callback,
            pattern=r"^season_\d+_\d+$",
        )
    )

    # --------------------------------------------------------
    # Episode selection
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            episode_callback,
            pattern=r"^episode_\d+_\d+_\d+$",
        )
    )

    # --------------------------------------------------------
    # Back to episodes
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            back_episodes_callback,
            pattern=r"^back_episodes_\d+_\d+$",
        )
    )

    # --------------------------------------------------------
    # Back to seasons
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            back_seasons_callback,
            pattern=r"^back_seasons_\d+$",
        )
    )

    # --------------------------------------------------------
    # Main menu
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            menu_callback,
            pattern=r"^menu_",
        )
    )

    # --------------------------------------------------------
    # SUPPORT
    # --------------------------------------------------------
    # This was missing in the previous version.
    # It handles:
    #
    # support
    # support_btc
    # support_ltc
    # support_bnb
    # support_eth
    # support_usdt
    # support_doge
    # support_trx
    # support_sol
    # support_back
    #
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            support_callback,
            pattern=r"^support(?:_.+)?$",
        )
    )