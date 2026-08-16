import html
import requests

from telegram import (
    Update,
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
    TMDB_API_KEY,
    TMDB_BASE_URL,
    TMDB_HEADERS,
    TMDB_IMAGE_BASE,
    BRAVE_PLAY_STORE_URL,
    CHANNEL_USERNAME,
    ADMIN_IDS,
)


# ============================================================
# TMDB
# ============================================================

def tmdb_get(endpoint, params=None):
    if not TMDB_API_KEY:
        raise RuntimeError(
            "TMDB_API_KEY is not configured."
        )

    request_params = dict(params or {})

    request_params["api_key"] = TMDB_API_KEY

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

    return date[:4] if date else "N/A"


def get_poster_url(item):
    path = item.get("poster_path")

    if not path:
        return None

    return f"{TMDB_IMAGE_BASE}{path}"


def get_item_type(item):
    if item.get("media_type") == "tv":
        return "TV Show"

    if item.get("media_type") == "movie":
        return "Movie"

    if item.get("first_air_date"):
        return "TV Show"

    return "Movie"


def get_vidsrc_url(item):
    item_id = item.get("id")

    if not item_id:
        return None

    if get_item_type(item) == "TV Show":
        return f"https://vidsrc.to/embed/tv/{item_id}"

    return f"https://vidsrc.to/embed/movie/{item_id}"


# ============================================================
# MAINTENANCE
# ============================================================

def is_admin(user_id):
    return user_id in ADMIN_IDS


async def maintenance_guard(update):
    user = update.effective_user

    if not user:
        return False

    if is_admin(user.id):
        return False

    if db.is_maintenance():
        await update.effective_message.reply_text(
            "🔧 <b>Bot Maintenance</b>\n\n"
            "The bot is temporarily under maintenance.\n"
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

    # Admins bypass membership requirement.
    if is_admin(user.id):
        return True

    if not CHANNEL_USERNAME:
        return True

    try:
        member = await context.bot.get_chat_member(
            f"@{CHANNEL_USERNAME.lstrip('@')}",
            user.id,
        )

        status = member.status

        if status in (
            "member",
            "administrator",
            "creator",
        ):
            return True

    except Exception:
        pass

    await update.effective_message.reply_text(
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
# COMMON ACCESS CHECK
# ============================================================

async def user_access_allowed(
    update,
    context,
):
    if await maintenance_guard(update):
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
    year = get_year(item)
    item_type = get_item_type(item)

    rating = item.get(
        "vote_average",
        0,
    )

    try:
        rating = float(rating)
    except (TypeError, ValueError):
        rating = 0.0

    overview = (
        item.get("overview")
        or "No description available."
    )

    overview = overview.strip()

    if len(overview) > 500:
        overview = overview[:497] + "..."

    watch_url = get_vidsrc_url(item)
    poster_url = get_poster_url(item)

    if not watch_url:
        raise RuntimeError(
            "Could not create playback URL."
        )

    caption = (
        f"🎬 <b>{html.escape(title)}</b>\n\n"
        f"📺 Type: {item_type}\n"
        f"📅 Year: {year}\n"
        f"⭐ Rating: {rating:.1f}\n\n"
        f"{html.escape(overview)}\n\n"
        f"👇 <b>Click below to watch</b>\n"
        f"🦁 Best experienced with Brave Browser."
    )

    markup = kb.movie_keyboard(
        watch_url=watch_url,
        brave_url=BRAVE_PLAY_STORE_URL,
        back_callback=back_callback,
    )

    if is_channel:
        channel_id = db.get_channel_id()

        if not channel_id:
            from config import CHANNEL_ID
            channel_id = CHANNEL_ID

        if not channel_id:
            raise RuntimeError(
                "CHANNEL_ID is not configured."
            )

        chat_id = channel_id

    else:
        chat_id = update.effective_chat.id

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

async def start(update, context):
    user = update.effective_user

    if user:
        db.save_user(
            user.id,
            user.username,
            user.first_name,
            user.last_name,
        )

    if await maintenance_guard(update):
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
        "📋 <code>/help</code>",
        parse_mode="HTML",
        reply_markup=kb.main_menu(),
    )


# ============================================================
# HELP
# ============================================================

async def help_cmd(update, context):
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
        "Popular movies.\n\n"
        "🏆 <code>/toprated</code>\n"
        "Top rated movies.",
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
        title = html.escape(
            get_title(item)
        )

        year = get_year(item)

        rating = item.get(
            "vote_average",
            0,
        )

        try:
            rating = float(rating)
        except Exception:
            rating = 0

        lines.append(
            f"<b>{index}.</b> "
            f"{title} "
            f"({year}) ⭐ {rating:.1f}"
        )

    lines.extend([
        "",
        f"Showing {start + 1}-{end} "
        f"of {len(results)} results.",
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
        title = get_title(item)

        if len(title) > 30:
            title = title[:27] + "..."

        year = get_year(item)

        text = f"{index}. {title}"

        if year != "N/A":
            text += f" ({year})"

        item_id = item.get("id")

        if not item_id:
            continue

        keyboard.append([
            kb.inline_button(
                text,
                f"select_{media_type}_{item_id}",
            )
        ])

    navigation = []

    if page > 0:
        navigation.append(
            kb.inline_button(
                "⬅️ Previous",
                f"results_{media_type}_{page - 1}",
            )
        )

    if end < len(results):
        navigation.append(
            kb.inline_button(
                "Next ➡️",
                f"results_{media_type}_{page + 1}",
            )
        )

    if navigation:
        keyboard.append(navigation)

    keyboard.append([
        kb.inline_button(
            "❌ Cancel",
            "results_cancel",
        )
    ])

    return InlineKeyboardMarkup(keyboard)


def store_results(
    context,
    results,
    search_query,
    media_type,
):
    context.user_data["search_results"] = results
    context.user_data["search_query"] = search_query
    context.user_data["search_media_type"] = media_type


# ============================================================
# MOVIE SEARCH
# ============================================================

async def movie_search_cmd(update, context):
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

    search_query = " ".join(context.args)

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
            x for x in data.get("results", [])
            if x.get("id")
        ][:20]

        if not results:
            await update.effective_message.reply_text(
                "❌ No movies found.",
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
            f"❌ TMDB error: "
            f"<code>{html.escape(str(exc))}</code>",
            parse_mode="HTML",
        )


# ============================================================
# TV SEARCH
# ============================================================

async def tvshow_search_cmd(update, context):
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

    search_query = " ".join(context.args)

    try:
        data = tmdb_get(
            "/search/tv",
            {
                "query": search_query,
                "page": 1,
            },
        )

        results = [
            x for x in data.get("results", [])
            if x.get("id")
        ][:20]

        if not results:
            await update.effective_message.reply_text(
                "❌ No TV shows found.",
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
            f"❌ TMDB error: "
            f"<code>{html.escape(str(exc))}</code>",
            parse_mode="HTML",
        )


# ============================================================
# SELECT MOVIE / TV
# ============================================================

async def select_result_callback(update, context):
    query = update.callback_query

    await query.answer()

    parts = query.data.split("_")

    if len(parts) != 3:
        return

    _, media_type, item_id = parts

    try:
        item_id = int(item_id)
    except ValueError:
        return

    try:
        endpoint = (
            f"/movie/{item_id}"
            if media_type == "movie"
            else f"/tv/{item_id}"
        )

        item = tmdb_get(endpoint)

        item["media_type"] = media_type

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
            f"❌ TMDB error:\n"
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

    parts = query.data.split("_")

    if len(parts) != 3:
        return

    _, media_type, page_text = parts

    try:
        page = int(page_text)
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
            "⚠️ Search expired. Please search again."
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

    await query.edit_message_text(
        "❌ Search cancelled."
    )


# ============================================================
# SEASONS SEARCH
# ============================================================

async def seasons_cmd(update, context):
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

    search_query = " ".join(context.args)

    try:
        data = tmdb_get(
            "/search/tv",
            {
                "query": search_query,
                "page": 1,
            },
        )

        results = [
            x for x in data.get("results", [])
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
            title = get_title(item)
            year = get_year(item)

            if len(title) > 30:
                title = title[:27] + "..."

            keyboard.append([
                kb.inline_button(
                    f"📺 {title} ({year})",
                    f"season_show_{item['id']}",
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
            f"❌ TMDB error: "
            f"{html.escape(str(exc))}",
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

    show_id = int(
        query.data.split("_")[-1]
    )

    try:
        details = tmdb_get(
            f"/tv/{show_id}"
        )

        seasons = details.get(
            "seasons",
            [],
        )

        seasons = [
            s for s in seasons
            if s.get("season_number") != 0
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
                    f"📀 Season {number} "
                    f"({episodes} episodes)",
                    f"season_{show_id}_{number}",
                )
            ])

        keyboard.append([
            kb.inline_button(
                "🔙 Back to TV Results",
                "seasons_back",
            )
        ])

        await query.edit_message_text(
            f"📺 <b>{html.escape(details.get('name', 'TV Show'))}</b>\n\n"
            "Choose a season:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
        )

    except Exception as exc:
        await query.message.reply_text(
            f"❌ TMDB error: "
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

    parts = query.data.split("_")

    show_id = int(parts[1])
    season_number = int(parts[2])

    try:
        data = tmdb_get(
            f"/tv/{show_id}/season/{season_number}"
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
                name = name[:32] + "..."

            keyboard.append([
                kb.inline_button(
                    f"▶️ {episode_number}. {name}",
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
            f"📺 <b>Season {season_number}</b>\n\n"
            "Choose an episode:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
        )

    except Exception as exc:
        await query.message.reply_text(
            f"❌ TMDB error: "
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

    parts = query.data.split("_")

    show_id = int(parts[1])
    season_number = int(parts[2])
    episode_number = int(parts[3])

    watch_url = (
        f"https://vidsrc.to/embed/tv/"
        f"{show_id}/"
        f"{season_number}-"
        f"{episode_number}"
    )

    markup = kb.movie_keyboard(
        watch_url,
        BRAVE_PLAY_STORE_URL,
        f"back_episodes_{show_id}_{season_number}",
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
# BACK TO SEASONS
# ============================================================

async def back_seasons_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    show_id = int(
        query.data.split("_")[-1]
    )

    try:
        details = tmdb_get(
            f"/tv/{show_id}"
        )

        seasons = [
            s for s in details.get(
                "seasons",
                []
            )
            if s.get("season_number") != 0
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
                    f"📀 Season {number} "
                    f"({episodes} episodes)",
                    f"season_{show_id}_{number}",
                )
            ])

        await query.edit_message_text(
            f"📺 <b>{html.escape(details.get('name', 'TV Show'))}</b>\n\n"
            "Choose a season:",
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
# POPULAR
# ============================================================

async def popular_cmd(update, context):
    if not await user_access_allowed(
        update,
        context,
    ):
        return

    try:
        data = tmdb_get(
            "/movie/popular",
            {"page": 1},
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

        await send_post_with_buttons(
            update,
            context,
            movies[0],
        )

    except Exception as exc:
        await update.effective_message.reply_text(
            f"❌ TMDB error: "
            f"{html.escape(str(exc))}",
            parse_mode="HTML",
        )


# ============================================================
# TOP RATED
# ============================================================

async def toprated_cmd(update, context):
    if not await user_access_allowed(
        update,
        context,
    ):
        return

    try:
        data = tmdb_get(
            "/movie/top_rated",
            {"page": 1},
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

        await send_post_with_buttons(
            update,
            context,
            movies[0],
        )

    except Exception as exc:
        await update.effective_message.reply_text(
            f"❌ TMDB error: "
            f"{html.escape(str(exc))}",
            parse_mode="HTML",
        )


# ============================================================
# MEMBERSHIP CHECK BUTTON
# ============================================================

async def membership_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    user = update.effective_user

    try:
        member = await context.bot.get_chat_member(
            f"@{CHANNEL_USERNAME.lstrip('@')}",
            user.id,
        )

        if member.status in (
            "member",
            "administrator",
            "creator",
        ):
            await query.message.reply_text(
                "✅ <b>Membership verified!</b>\n\n"
                "🎬 Welcome to MovieBot.",
                parse_mode="HTML",
                reply_markup=kb.main_menu(),
            )
        else:
            await query.message.reply_text(
                "😂 <b>Hahaha 😀 I can find you there!</b>\n\n"
                "Join the channel first 😉",
                parse_mode="HTML",
                reply_markup=kb.join_channel_keyboard(
                    CHANNEL_USERNAME
                ),
            )

    except Exception:
        await query.message.reply_text(
            "😂 <b>Hahaha 😀 I can find you there!</b>\n\n"
            "Join the channel first 😉",
            parse_mode="HTML",
            reply_markup=kb.join_channel_keyboard(
                CHANNEL_USERNAME
            ),
        )


# ============================================================
# MAIN MENU CALLBACK
# ============================================================

async def menu_callback(
    update,
    context,
):
    query = update.callback_query

    await query.answer()

    if await maintenance_guard(update):
        return

    action = query.data

    if action == "menu_movie":
        await query.message.reply_text(
            "🎬 Send:\n"
            "<code>/movie Movie Name</code>",
            parse_mode="HTML",
        )

    elif action == "menu_tv":
        await query.message.reply_text(
            "📺 Send:\n"
            "<code>/tvshow TV Show Name</code>",
            parse_mode="HTML",
        )

    elif action == "menu_popular":
        await popular_cmd(update, context)

    elif action == "menu_toprated":
        await toprated_cmd(update, context)

    elif action == "menu_help":
        await help_cmd(update, context)


# ============================================================
# REGISTER
# ============================================================

def register(app: Application):

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

    # Membership
    app.add_handler(
        CallbackQueryHandler(
            membership_callback,
            pattern=r"^check_membership$",
        )
    )

    # Movie / TV selection
    app.add_handler(
        CallbackQueryHandler(
            select_result_callback,
            pattern=r"^select_(movie|tv)_\d+$",
        )
    )

    # Search pagination
    app.add_handler(
        CallbackQueryHandler(
            results_page_callback,
            pattern=r"^results_(movie|tv)_\d+$",
        )
    )

    # Cancel
    app.add_handler(
        CallbackQueryHandler(
            results_cancel_callback,
            pattern=r"^results_cancel$",
        )
    )

    # TV seasons search
    app.add_handler(
        CallbackQueryHandler(
            season_show_callback,
            pattern=r"^season_show_\d+$",
        )
    )

    # Season selection
    app.add_handler(
        CallbackQueryHandler(
            season_callback,
            pattern=r"^season_\d+_\d+$",
        )
    )

    # Episode selection
    app.add_handler(
        CallbackQueryHandler(
            episode_callback,
            pattern=r"^episode_\d+_\d+_\d+$",
        )
    )

    # Back to seasons
    app.add_handler(
        CallbackQueryHandler(
            back_seasons_callback,
            pattern=r"^back_seasons_\d+$",
        )
    )

    # Main menu
    app.add_handler(
        CallbackQueryHandler(
            menu_callback,
            pattern=r"^menu_",
        )
    )