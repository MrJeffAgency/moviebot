import hashlib
import html
import hmac as _hmac
import json
import os
import re
from datetime import datetime, timezone
from secrets import compare_digest

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()

ADMIN_IDS = set()
raw_ids = os.getenv("ADMIN_IDS", "").strip()
if raw_ids:
    for value in re.split(r"[,\s]+", raw_ids):
        if value.strip().isdigit():
            ADMIN_IDS.add(int(value))
legacy_admin = os.getenv("ADMIN_ID", "").strip()
if legacy_admin.isdigit():
    ADMIN_IDS.add(int(legacy_admin))

CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip()
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "").strip()
BRAVE_PLAY_STORE_URL = os.getenv(
    "BRAVE_PLAY_STORE_URL",
    "https://play.google.com/store/apps/details?id=com.brave.browser",
).strip()

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").strip()
TMDB_BASE_URL = os.getenv("TMDB_BASE_URL", "https://api.themoviedb.org/3").strip().rstrip("/")
TMDB_IMAGE_BASE = os.getenv("TMDB_IMAGE_BASE", "https://image.tmdb.org/t/p/w500").strip().rstrip("/")

BTC_WALLET = os.getenv("BTC_WALLET", "").strip()
LTC_WALLET = os.getenv("LTC_WALLET", "").strip()
BNB_WALLET = os.getenv("BNB_WALLET", "").strip()
ETH_WALLET = os.getenv("ETH_WALLET", "").strip()
USDT_WALLET = os.getenv("USDT_WALLET", "").strip()
DOGE_WALLET = os.getenv("DOGE_WALLET", "").strip()
TRX_WALLET = os.getenv("TRX_WALLET", "").strip()
SOL_WALLET = os.getenv("SOL_WALLET", "").strip()

KV_URL = os.getenv("KV_REST_API_URL", "").strip().rstrip("/")
KV_TOKEN = os.getenv("KV_REST_API_TOKEN", "").strip()

STATE_KEY = "moviebot_state"

USER_STATE = {}
_hydrated = False


def ts_now():
    return datetime.now(timezone.utc).isoformat()


def load_state():
    global _users, _searches, _settings, _hydrated
    if _hydrated:
        return
    _hydrated = True
    if not KV_URL or not KV_TOKEN:
        return
    try:
        raw = kv_get(STATE_KEY)
        if raw:
            data = json.loads(raw)
            _users.update(data.get("users", {}))
            _searches.extend(data.get("searches", []))
            _settings.update(data.get("settings", {}))
    except Exception:
        pass


def save_state():
    if not KV_URL or not KV_TOKEN:
        return
    try:
        kv_set(
            STATE_KEY,
            json.dumps(
                {"users": _users, "searches": _searches, "settings": _settings},
                separators=(",", ":"),
            ),
        )
    except Exception:
        pass


def kv_get(key):
    url = f"{KV_URL}/get/{key}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {KV_TOKEN}"}, timeout=10)
    data = resp.json()
    if data.get("error"):
        raise RuntimeError(data["error"])
    return data.get("result")


def kv_set(key, value):
    url = f"{KV_URL}/set/{key}/{value}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {KV_TOKEN}"}, timeout=10)
    data = resp.json()
    if data.get("error"):
        raise RuntimeError(data["error"])
    return data.get("result")


_users = {}
_searches = []
_settings = {}


def save_user(user):
    uid = user.get("id")
    if not uid:
        return
    now = ts_now()
    existing = _users.get(str(uid))
    if existing is None:
        _users[str(uid)] = {
            "id": uid,
            "username": user.get("username"),
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "joined_at": now,
            "last_seen": now,
        }
    else:
        existing["username"] = user.get("username")
        existing["first_name"] = user.get("first_name")
        existing["last_name"] = user.get("last_name")
        existing["last_seen"] = now
    save_state()


def get_user_count():
    return len(_users)


def get_recent_users(limit=15):
    rows = sorted(_users.values(), key=lambda r: r["joined_at"], reverse=True)[:limit]
    return [
        (
            r["id"],
            r.get("username"),
            r.get("first_name"),
            r.get("last_name"),
            r["joined_at"],
            r.get("last_seen"),
        )
        for r in rows
    ]


def list_all_users():
    return sorted(_users.values(), key=lambda r: r.get("last_seen") or "", reverse=True)


def save_search(user_id, query, search_type):
    _searches.append(
        {"user_id": user_id, "query": query, "search_type": search_type, "created_at": ts_now()}
    )
    save_state()


def get_search_count():
    return len(_searches)


def get_setting(key, default=None):
    return _settings.get(key, default)


def set_setting(key, value):
    _settings[key] = str(value)
    save_state()


def is_maintenance():
    return get_setting("maintenance", "0") == "1"


def set_maintenance(enabled):
    set_setting("maintenance", "1" if enabled else "0")


def get_channel_id():
    return get_setting("channel_id") or CHANNEL_ID


def set_channel_id(value):
    set_setting("channel_id", value)


def tg(method, **payload):
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not configured.")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    resp = requests.post(url, json=payload, timeout=30)
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", method + " failed"))
    return data.get("result")


def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    if parse_mode:
        payload["parse_mode"] = parse_mode
    return tg("sendMessage", **payload)


def send_photo(chat_id, photo, caption=None, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "photo": photo}
    if caption:
        payload["caption"] = caption
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    if parse_mode:
        payload["parse_mode"] = parse_mode
    return tg("sendPhoto", **payload)


def edit_message_text(message_or_chat, text, reply_markup=None, parse_mode="HTML"):
    payload = {"text": text}
    if isinstance(message_or_chat, dict) and "chat" in message_or_chat:
        payload["chat_id"] = message_or_chat["chat"]["id"]
        payload["message_id"] = message_or_chat["message_id"]
    else:
        payload["chat_id"] = message_or_chat.get("chat", {}).get("id")
        payload["message_id"] = message_or_chat.get("message_id")
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    if parse_mode:
        payload["parse_mode"] = parse_mode
    return tg("editMessageText", **payload)


def answer_callback(callback_id, text=None):
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
    return tg("answerCallbackQuery", **payload)


def tmdb_get(endpoint, params=None):
    if not TMDB_API_KEY:
        raise RuntimeError("TMDB_API_KEY is not configured.")
    request_params = dict(params or {})
    request_params["api_key"] = TMDB_API_KEY
    resp = requests.get(f"{TMDB_BASE_URL}{endpoint}", params=request_params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def inline_button(text, callback_data):
    return {"text": text, "callback_data": callback_data}


def markups_keyboard(rows):
    return {"inline_keyboard": rows}


def main_menu():
    return markups_keyboard(
        [
            [inline_button("🎬 Movies", "menu_movie"), inline_button("📺 TV Shows", "menu_tv")],
            [inline_button("💰 Support", "support")],
            [inline_button("🌟 Popular", "menu_popular"), inline_button("🏆 Top Rated", "menu_toprated")],
            [inline_button("📋 Help", "menu_help")],
        ]
    )


def movie_keyboard(watch_url, brave_url=None, back_callback=None):
    rows = [[{"text": "▶️ Watch Now", "url": watch_url}]]
    if brave_url:
        rows.append([{"text": "🦁 Open Brave", "url": brave_url}])
    if back_callback:
        rows.append([inline_button("🔙 Back to Seasons", back_callback)])
    return {"inline_keyboard": rows}


def join_channel_keyboard(channel_username):
    username = channel_username.lstrip("@")
    return markups_keyboard(
        [
            [{"text": "📢 Join Telegram Channel", "url": f"https://t.me/{username}"}],
            [inline_button("✅ Done — Check Membership", "check_membership")],
        ]
    )


def admin_home(maintenance=False):
    text = "⏹ Maintenance: ON" if maintenance else "▶️ Maintenance: OFF"
    return markups_keyboard(
        [
            [inline_button("🎬 Post Movie", "admin_post_movie"), inline_button("📺 Post TV Show", "admin_post_tv")],
            [inline_button("👻 Top 3 Horror", "admin_horror")],
            [inline_button("📊 Statistics", "admin_stats"), inline_button("👥 Recent Users", "admin_users")],
            [inline_button(text, "admin_maintenance")],
            [inline_button("⚙️ Channel Settings", "admin_channel"), inline_button("🆔 Admin ID", "admin_id")],
        ]
    )


def back_admin():
    return markups_keyboard([[inline_button("🔙 Back to Admin Panel", "admin_home")]])


def channel_settings_keyboard():
    return markups_keyboard(
        [
            [inline_button("🔄 Refresh", "admin_channel")],
            [inline_button("🔙 Back", "admin_home")],
        ]
    )


def admin_post_menu():
    return markups_keyboard(
        [
            [inline_button("🎬 Post Movie", "admin_post_movie")],
            [inline_button("📺 Post TV Show", "admin_post_tv")],
            [inline_button("🔙 Back", "admin_home")],
        ]
    )


def support_keyboard():
    return markups_keyboard(
        [
            [inline_button("₿ Bitcoin", "support_btc"), inline_button("Ł Litecoin", "support_ltc")],
            [inline_button("🟡 BNB", "support_bnb"), inline_button("♦️ Ethereum", "support_eth")],
            [inline_button("💵 USDT", "support_usdt"), inline_button("🐕 Dogecoin", "support_doge")],
            [inline_button("🔺 TRON", "support_trx"), inline_button("☀️ Solana", "support_sol")],
            [inline_button("🔙 Back to Menu", "support_back")],
        ]
    )


def get_title(item):
    return item.get("title") or item.get("name") or "Unknown"


def get_year(item):
    date = item.get("release_date") or item.get("first_air_date") or ""
    return date[:4] if date else "N/A"


def get_rating(item):
    try:
        return float(item.get("vote_average") or 0)
    except (TypeError, ValueError):
        return 0.0


def get_poster_url(item):
    path = item.get("poster_path")
    if not path:
        return None
    return f"{TMDB_IMAGE_BASE}{path}"


def get_item_type(item):
    media_type = item.get("media_type")
    if media_type == "tv":
        return "TV Show"
    if media_type == "movie":
        return "Movie"
    if item.get("first_air_date"):
        return "TV Show"
    return "Movie"


def get_watch_url(item):
    item_id = item.get("id")
    if not item_id:
        return None
    if get_item_type(item) == "TV Show":
        return f"https://vidsrc.to/embed/tv/{item_id}"
    return f"https://vidsrc.to/embed/movie/{item_id}"


def clean_overview(overview, maximum=500):
    overview = (overview or "No description available.").strip()
    if len(overview) > maximum:
        overview = overview[: maximum - 3] + "..."
    return overview


def is_admin(user_id):
    return user_id in ADMIN_IDS


def check_membership(bot, user_id):
    if user_id in ADMIN_IDS:
        return True
    if not CHANNEL_USERNAME:
        return True
    try:
        member = tg("getChatMember", chat_id=f"@{CHANNEL_USERNAME.lstrip('@')}", user_id=user_id)
        return member.get("status") in ("member", "administrator", "creator")
    except Exception:
        return None


def send_post_with_buttons(chat_id, item, back_callback=None):
    title = get_title(item)
    item_year = get_year(item)
    item_type = get_item_type(item)
    rating = get_rating(item)
    overview = clean_overview(item.get("overview"))
    watch_url = get_watch_url(item)
    poster_url = get_poster_url(item)
    if not watch_url:
        raise RuntimeError("Could not create playback URL.")
    caption = (
        f"🎬 <b>{html.escape(title)}</b>\n\n"
        f"📺 Type: {html.escape(item_type)}\n"
        f"📅 Year: {html.escape(item_year)}\n"
        f"⭐ Rating: {rating:.1f}\n\n"
        f"{html.escape(overview)}\n\n"
        "👇 <b>Click below to watch</b>\n"
        "🦁 Best experienced with Brave Browser."
    )
    markup = movie_keyboard(watch_url, BRAVE_PLAY_STORE_URL, back_callback)
    if poster_url:
        send_photo(chat_id, poster_url, caption, markup)
    else:
        send_message(chat_id, caption, markup)


def send_channel_post(item, media_type):
    channel_id = get_channel_id()
    if not channel_id:
        raise RuntimeError("CHANNEL_ID is not configured.")
    item_title = get_title(item)
    item_year = get_year(item)
    item_rating = get_rating(item)
    overview = clean_overview(item.get("overview"))
    url = get_watch_url(item)
    if not url:
        raise RuntimeError("Could not create watch URL.")
    item_type = "TV Show" if media_type == "tv" else "Movie"
    caption = (
        f"🎬 <b>{html.escape(item_title)}</b>\n\n"
        f"📺 Type: {item_type}\n"
        f"📅 Year: {html.escape(item_year)}\n"
        f"⭐ Rating: {item_rating:.1f}\n\n"
        f"{html.escape(overview)}\n\n"
        "👇 <b>Click below to watch</b>"
    )
    markup = movie_keyboard(url, BRAVE_PLAY_STORE_URL)
    image = get_poster_url(item)
    if image:
        send_photo(channel_id, image, caption, markup)
    else:
        send_message(channel_id, caption, markup)


def build_results_text(results, query, media_type, page=0, per_page=10):
    start = page * per_page
    end = min(start + per_page, len(results))
    heading = "🎬 Movie Results" if media_type == "movie" else "📺 TV Show Results"
    lines = ["<b>" + heading + "</b>", "", "🔎 <b>" + html.escape(query) + "</b>", "", "👇 Choose a title:", ""]
    for index, item in enumerate(results[start:end], start=start + 1):
        item_title = html.escape(get_title(item))
        item_year = get_year(item)
        rating = get_rating(item)
        lines.append(f"<b>{index}.</b> {item_title} ({item_year}) ⭐ {rating:.1f}")
    if start < end:
        showing = f"Showing {start + 1}-{end} of {len(results)} results."
    else:
        showing = f"No results on page {page + 1}."
    lines.extend(["", showing])
    return "\n".join(lines)


def build_search_keyboard(results, media_type, page=0, per_page=10):
    start = page * per_page
    end = start + per_page
    keyboard = []
    for index, item in enumerate(results[start:end], start=start + 1):
        item_title = get_title(item)
        if len(item_title) > 30:
            item_title = item_title[:27] + "..."
        item_year = get_year(item)
        text = f"{index}. {item_title}"
        if item_year != "N/A":
            text += f" ({item_year})"
        item_id = item.get("id")
        if not item_id:
            continue
        keyboard.append([inline_button(text, f"select_{media_type}_{item_id}")])
    navigation = []
    if page > 0:
        navigation.append(inline_button("⬅️ Previous", f"results_{media_type}_{page - 1}"))
    if end < len(results):
        navigation.append(inline_button("Next ➡️", f"results_{media_type}_{page + 1}"))
    if navigation:
        keyboard.append(navigation)
    keyboard.append([inline_button("❌ Cancel", "results_cancel")])
    return markups_keyboard(keyboard)


def maintenance_guard(chat_id, message):
    if is_admin(chat_id):
        return False
    if is_maintenance():
        send_message(chat_id, "🔧 <b>Bot Maintenance</b>\n\nThe bot is temporarily under maintenance.\n\nPlease try again later. 🛠️")
        return True
    return False


def user_access_allowed(chat_id, message):
    if maintenance_guard(chat_id, message):
        return False
    membership = check_membership(None, chat_id)
    if membership is False:
        send_message(chat_id, "🔐 <b>Join our Telegram channel first</b>\n\nJoin the channel and then press <b>Done — Check Membership</b>.", join_channel_keyboard(CHANNEL_USERNAME))
        return False
    return True


def handle_start(chat_id, user):
    save_user(user)
    if is_maintenance() and not is_admin(chat_id):
        send_message(chat_id, "🔧 <b>Bot Maintenance</b>\n\nThe bot is temporarily under maintenance.\n\nPlease try again later. 🛠️")
        return
    membership = check_membership(None, chat_id)
    if membership is False:
        send_message(chat_id, "🔐 <b>Join our Telegram channel first</b>\n\nJoin the channel and then press <b>Done — Check Membership</b>.", join_channel_keyboard(CHANNEL_USERNAME))
        return
    send_message(
        chat_id,
        "🎬 <b>Welcome to MovieBot!</b>\n\n"
        "Search for movies and TV shows.\n\n"
        "🎬 <code>/movie Batman</code>\n"
        "📺 <code>/tvshow Breaking Bad</code>\n"
        "📺 <code>/seasons Breaking Bad</code>\n"
        "🌟 <code>/popular</code>\n"
        "🏆 <code>/toprated</code>\n"
        "📋 <code>/help</code>\n\n"
        "❤️ <b>Support</b> is available from the main menu.",
        main_menu(),
    )


def handle_help(chat_id):
    if not user_access_allowed(chat_id, None):
        return
    send_message(
        chat_id,
        "📋 <b>MovieBot Commands</b>\n\n"
        "🎬 <code>/movie Batman</code>\nSearch movies.\n\n"
        "📺 <code>/tvshow Breaking Bad</code>\nSearch TV shows.\n\n"
        "📺 <code>/seasons Breaking Bad</code>\nChoose a TV show and view seasons.\n\n"
        "🌟 <code>/popular</code>\nShow popular movies.\n\n"
        "🏆 <code>/toprated</code>\nShow top-rated movies.\n\n"
        "❤️ <b>Support</b>\nOpen the Support button from the main menu.",
    )


def store_results(user_id, results, query, media_type):
    USER_STATE.setdefault(str(user_id), {})["search"] = {
        "results": results,
        "query": query,
        "media_type": media_type,
    }


def user_state(user_id):
    return USER_STATE.setdefault(str(user_id), {})


def handle_movie_search(chat_id, user, query):
    if not user_access_allowed(chat_id, None):
        return
    data = tmdb_get("/search/movie", {"query": query, "page": 1, "include_adult": "false"})
    results = [x for x in data.get("results", []) if x.get("id")][:20]
    if not results:
        send_message(chat_id, "❌ No movies found.")
        return
    store_results(chat_id, results, query, "movie")
    send_message(chat_id, build_results_text(results, query, "movie"), build_search_keyboard(results, "movie"))
    save_search(user["id"], query, "movie")


def handle_tvshow_search(chat_id, user, query):
    if not user_access_allowed(chat_id, None):
        return
    data = tmdb_get("/search/tv", {"query": query, "page": 1})
    results = [x for x in data.get("results", []) if x.get("id")][:20]
    if not results:
        send_message(chat_id, "❌ No TV shows found.")
        return
    store_results(chat_id, results, query, "tv")
    send_message(chat_id, build_results_text(results, query, "tv"), build_search_keyboard(results, "tv"))
    save_search(user["id"], query, "tv")


def handle_seasons(chat_id, user, query):
    if not user_access_allowed(chat_id, None):
        return
    data = tmdb_get("/search/tv", {"query": query, "page": 1})
    results = [x for x in data.get("results", []) if x.get("id")][:20]
    if not results:
        send_message(chat_id, "❌ No TV shows found.")
        return
    user_state(chat_id)["season_results"] = results
    keyboard = []
    for item in results:
        item_title = get_title(item)
        item_year = get_year(item)
        if len(item_title) > 30:
            item_title = item_title[:27] + "..."
        keyboard.append([inline_button(f"📺 {item_title} ({item_year})", f"season_show_{item['id']}")])
    keyboard.append([inline_button("❌ Cancel", "results_cancel")])
    send_message(chat_id, f"📺 <b>Choose a TV Show</b>\n\nSearch: <b>{html.escape(query)}</b>", markups_keyboard(keyboard))


def handle_popular(chat_id):
    if not user_access_allowed(chat_id, None):
        return
    data = tmdb_get("/movie/popular", {"page": 1})
    movies = data.get("results", [])
    if not movies:
        send_message(chat_id, "❌ No popular movies found.")
        return
    item = movies[0]
    item["media_type"] = "movie"
    send_post_with_buttons(chat_id, item)


def handle_toprated(chat_id):
    if not user_access_allowed(chat_id, None):
        return
    data = tmdb_get("/movie/top_rated", {"page": 1})
    movies = data.get("results", [])
    if not movies:
        send_message(chat_id, "❌ No top-rated movies found.")
        return
    item = movies[0]
    item["media_type"] = "movie"
    send_post_with_buttons(chat_id, item)


def handle_select(messages, callback_id, user, data):
    parts = data.split("_")
    if len(parts) != 3:
        return
    _, media_type, item_id_text = parts
    try:
        item_id = int(item_id_text)
    except ValueError:
        return
    if media_type not in ("movie", "tv"):
        return
    endpoint = f"/movie/{item_id}" if media_type == "movie" else f"/tv/{item_id}"
    item = tmdb_get(endpoint)
    item["media_type"] = media_type
    edit_message_text(messages, "⏳ Loading...")
    if media_type == "tv":
        user_state(user["id"])["selected_tv_id"] = item_id
    send_post_with_buttons(messages["chat"]["id"], item)


def handle_results_page(messages, data):
    parts = data.split("_")
    if len(parts) != 3:
        return
    _, media_type, page_text = parts
    try:
        page = int(page_text)
    except ValueError:
        return
    chat_id = messages["chat"]["id"]
    st = user_state(chat_id).get("search")
    if not st or not st.get("results"):
        edit_message_text(messages, "⚠️ Search expired. Please search again.")
        return
    edit_message_text(messages, build_results_text(st["results"], st["query"], media_type, page), build_search_keyboard(st["results"], media_type, page))


def handle_search_cancel(messages):
    chat_id = messages["chat"]["id"]
    user_state(chat_id).pop("search", None)
    edit_message_text(messages, "❌ Search cancelled.")


def handle_season_show(messages, data):
    try:
        show_id = int(data.split("_")[-1])
    except ValueError:
        return
    details = tmdb_get(f"/tv/{show_id}")
    seasons = [s for s in details.get("seasons", []) if s.get("season_number") != 0]
    if not seasons:
        send_message(messages["chat"]["id"], "❌ No seasons found.")
        return
    user_state(messages["chat"]["id"])["current_tv_id"] = show_id
    user_state(messages["chat"]["id"])["current_tv_name"] = details.get("name", "TV Show")
    keyboard = []
    for season in seasons:
        number = season.get("season_number")
        episodes = season.get("episode_count", 0)
        keyboard.append([inline_button(f"📀 Season {number} ({episodes} episodes)", f"season_{show_id}_{number}")])
    keyboard.append([inline_button("🔙 Back to TV Results", "seasons_back")])
    edit_message_text(messages, f"📺 <b>{html.escape(details.get('name', 'TV Show'))}</b>\n\nChoose a season:", markups_keyboard(keyboard))


def handle_season(messages, data):
    parts = data.split("_")
    if len(parts) != 3:
        return
    try:
        show_id = int(parts[1])
        season_number = int(parts[2])
    except ValueError:
        return
    data_tmdb = tmdb_get(f"/tv/{show_id}/season/{season_number}")
    episodes = data_tmdb.get("episodes", [])
    chat_id = messages["chat"]["id"]
    if not episodes:
        send_message(chat_id, "❌ No episodes found.")
        return
    user_state(chat_id)["current_tv_id"] = show_id
    user_state(chat_id)["current_season"] = season_number
    keyboard = []
    for episode in episodes:
        episode_number = episode.get("episode_number")
        name = episode.get("name", "Episode")
        if len(name) > 35:
            name = name[:32] + "..."
        keyboard.append([inline_button(f"▶️ {episode_number}. {name}", f"episode_{show_id}_{season_number}_{episode_number}")])
    keyboard.append([inline_button("🔙 Back to Seasons", f"back_seasons_{show_id}")])
    edit_message_text(messages, f"📺 <b>Season {season_number}</b>\n\nChoose an episode:", markups_keyboard(keyboard))


def handle_episode(messages, data):
    parts = data.split("_")
    if len(parts) != 4:
        return
    try:
        show_id = int(parts[1])
        season_number = int(parts[2])
        episode_number = int(parts[3])
    except ValueError:
        return
    watch_url = f"https://vidsrc.to/embed/tv/{show_id}/{season_number}-{episode_number}"
    markup = movie_keyboard(watch_url, BRAVE_PLAY_STORE_URL, f"back_episodes_{show_id}_{season_number}")
    edit_message_text(messages, f"🎬 <b>Episode Ready</b>\n\n📺 Season {season_number}\n🎞 Episode {episode_number}\n\n👇 Click below to watch.", markup)


def handle_back_episodes(messages, data):
    parts = data.split("_")
    if len(parts) != 3:
        return
    try:
        show_id = int(parts[1])
        season_number = int(parts[2])
    except ValueError:
        return
    data_tmdb = tmdb_get(f"/tv/{show_id}/season/{season_number}")
    episodes = data_tmdb.get("episodes", [])
    chat_id = messages["chat"]["id"]
    if not episodes:
        edit_message_text(messages, "❌ No episodes found.")
        return
    keyboard = []
    for episode in episodes:
        episode_number = episode.get("episode_number")
        name = episode.get("name", "Episode")
        if len(name) > 35:
            name = name[:32] + "..."
        keyboard.append([inline_button(f"▶️ {episode_number}. {name}", f"episode_{show_id}_{season_number}_{episode_number}")])
    keyboard.append([inline_button("🔙 Back to Seasons", f"back_seasons_{show_id}")])
    edit_message_text(messages, f"📺 <b>Season {season_number}</b>\n\nChoose an episode:", markups_keyboard(keyboard))


def handle_back_seasons(messages, data):
    try:
        show_id = int(data.split("_")[-1])
    except ValueError:
        return
    details = tmdb_get(f"/tv/{show_id}")
    seasons = [s for s in details.get("seasons", []) if s.get("season_number") != 0]
    keyboard = []
    for season in seasons:
        number = season.get("season_number")
        episodes = season.get("episode_count", 0)
        keyboard.append([inline_button(f"📀 Season {number} ({episodes} episodes)", f"season_{show_id}_{number}")])
    edit_message_text(messages, f"📺 <b>{html.escape(details.get('name', 'TV Show'))}</b>\n\nChoose a season:", markups_keyboard(keyboard))


def handle_seasons_back(messages):
    chat_id = messages["chat"]["id"]
    results = user_state(chat_id).get("season_results")
    if not results:
        edit_message_text(messages, "⚠️ Previous search expired. Please use /seasons again.")
        return
    keyboard = []
    for item in results:
        item_title = get_title(item)
        item_year = get_year(item)
        if len(item_title) > 30:
            item_title = item_title[:27] + "..."
        keyboard.append([inline_button(f"📺 {item_title} ({item_year})", f"season_show_{item['id']}")])
    keyboard.append([inline_button("❌ Cancel", "results_cancel")])
    edit_message_text(messages, "📺 <b>Choose a TV Show</b>", markups_keyboard(keyboard))


def handle_menu(chat_id, data):
    if maintenance_guard(chat_id, None):
        return
    if data == "menu_movie":
        send_message(chat_id, "🎬 <b>Movie Search</b>\n\nSend:\n<code>/movie Movie Name</code>")
    elif data == "menu_tv":
        send_message(chat_id, "📺 <b>TV Show Search</b>\n\nSend:\n<code>/tvshow TV Show Name</code>")
    elif data == "menu_popular":
        handle_popular(chat_id)
    elif data == "menu_toprated":
        handle_toprated(chat_id)
    elif data == "menu_help":
        handle_help(chat_id)


SUPPORT_WALLETS = {
    "btc": ("₿ Bitcoin", BTC_WALLET),
    "ltc": ("Ł Litecoin", LTC_WALLET),
    "bnb": ("🟡 BNB", BNB_WALLET),
    "eth": ("♦️ Ethereum", ETH_WALLET),
    "usdt": ("💵 USDT", USDT_WALLET),
    "doge": ("🐕 Dogecoin", DOGE_WALLET),
    "trx": ("🔺 TRON", TRX_WALLET),
    "sol": ("☀️ Solana", SOL_WALLET),
}


def handle_support(chat_id, data):
    if maintenance_guard(chat_id, None):
        return
    if data == "support":
        send_message(
            chat_id,
            "❤️ <b>Support MovieBot</b>\n\n"
            "Thank you for supporting the bot! 🙏\n\n"
            "If you enjoy using MovieBot and would like to support the admin, "
            "you can donate using one of the wallets below.\n\n"
            "💰 <b>Choose your cryptocurrency:</b>",
            support_keyboard(),
        )
        return
    if data == "support_back":
        send_message(chat_id, "🏠 <b>Main Menu</b>", main_menu())
        return
    if not data.startswith("support_"):
        return
    coin = data.replace("support_", "", 1)
    wallet_data = SUPPORT_WALLETS.get(coin)
    if not wallet_data:
        send_message(chat_id, "❌ Unknown cryptocurrency.", support_keyboard())
        return
    coin_name, wallet = wallet_data
    if not wallet:
        send_message(
            chat_id,
            f"⚠️ <b>{html.escape(coin_name)}</b>\n\nThe admin has not configured a wallet address for this cryptocurrency yet.\n\nPlease choose another option.",
            support_keyboard(),
        )
        return
    send_message(
        chat_id,
        "🙏 <b>Thank you for supporting MovieBot!</b>\n\n"
        f"💰 <b>{html.escape(coin_name)}</b>\n\n"
        "📋 <b>Wallet Address</b>\n"
        f"<code>{html.escape(wallet)}</code>\n\n"
        "👆 Tap the wallet address above to copy it.\n\n"
        "❤️ Every contribution helps keep the bot running. Thank you!",
        support_keyboard(),
    )


def handle_membership(messages, user):
    if not CHANNEL_USERNAME:
        send_message(messages["chat"]["id"], "⚠️ Channel membership is not configured.")
        return
    try:
        member = tg("getChatMember", chat_id=f"@{CHANNEL_USERNAME.lstrip('@')}", user_id=user["id"])
        if member.get("status") in ("member", "administrator", "creator"):
            save_user(user)
            send_message(messages["chat"]["id"], "✅ <b>Membership verified!</b>\n\n🎬 Welcome to MovieBot.", main_menu())
        else:
            send_message(messages["chat"]["id"], "❌ <b>You are not a member yet.</b>\n\nJoin the channel first and press the button again.", join_channel_keyboard(CHANNEL_USERNAME))
    except Exception:
        send_message(messages["chat"]["id"], "⚠️ I couldn't verify membership.\n\nMake sure the bot is an administrator of the Telegram channel.", join_channel_keyboard(CHANNEL_USERNAME))


def show_admin_panel(chat_id, message_obj):
    text = "🔐 <b>MovieBot Admin Panel</b>\n\n" + f"🔧 Maintenance: <b>{'ON ⏹' if is_maintenance() else 'OFF ▶️'}</b>\n\nChoose an option below:"
    markup = admin_home(is_maintenance())
    if message_obj is None or not isinstance(message_obj, dict):
        send_message(chat_id, text, markup)
    else:
        edit_message_text(message_obj, text, markup)


def handle_admin_command(chat_id, user, message_obj=None):
    if not is_admin(user["id"]):
        send_message(chat_id, "🚫 <b>Access Denied</b>")
        return
    show_admin_panel(chat_id, message_obj)


def handle_admin_home(chat_id, user, message_obj):
    if not is_admin(user["id"]):
        return
    user_state(user["id"]).pop("admin_post", None)
    show_admin_panel(chat_id, message_obj)


def handle_admin_maintenance(chat_id, user, message_obj):
    if not is_admin(user["id"]):
        return
    new_state = not is_maintenance()
    set_maintenance(new_state)
    status = "⏹ ON" if new_state else "▶️ OFF"
    edit_message_text(
        message_obj,
        "🔧 <b>Maintenance Mode</b>\n\nStatus: <b>" + status + "</b>\n\n" + ("⚠️ Normal users are now blocked." if new_state else "✅ Normal users can use the bot."),
        back_admin(),
    )


def handle_admin_stats(chat_id, user, message_obj):
    if not is_admin(user["id"]):
        return
    users = get_user_count()
    searches = get_search_count()
    maintenance = "ON ⏹" if is_maintenance() else "OFF ▶️"
    edit_message_text(
        message_obj,
        "📊 <b>Bot Statistics</b>\n\n"
        f"👥 Total Users: <b>{users}</b>\n"
        f"🔎 Total Searches: <b>{searches}</b>\n"
        f"🔧 Maintenance: <b>{maintenance}</b>",
        back_admin(),
    )


def handle_admin_users(chat_id, user, message_obj):
    if not is_admin(user["id"]):
        return
    users = get_recent_users(15)
    if not users:
        text = "👥 <b>Recent Users</b>\n\nNo users registered yet."
    else:
        lines = ["👥 <b>Recent Users</b>", ""]
        for user_id, username, first_name, last_name, joined_at, last_seen in users:
            display_name = first_name or username or str(user_id)
            if username:
                display_name += f" @{username}"
            lines.append(f"• <b>{html.escape(str(display_name))}</b>\n  ID: <code>{user_id}</code>")
        text = "\n".join(lines)
    edit_message_text(message_obj, text, back_admin())


def handle_admin_id(chat_id, user, message_obj):
    if not is_admin(user["id"]):
        return
    ids = "\n".join(f"• <code>{x}</code>" for x in sorted(ADMIN_IDS))
    if not ids:
        ids = "⚠️ No ADMIN_IDS configured."
    edit_message_text(message_obj, f"🆔 <b>Configured Admin IDs</b>\n\n{ids}\n\nYour ID:\n<code>{user['id']}</code>", back_admin())


def handle_admin_channel(chat_id, user, message_obj):
    if not is_admin(user["id"]):
        return
    configured = get_channel_id() or "Not configured"
    edit_message_text(
        message_obj,
        "⚙️ <b>Channel Settings</b>\n\nChannel ID:\n"
        + f"<code>{html.escape(str(configured))}</code>\n\n"
        + "The channel ID is normally configured in your .env file.",
        channel_settings_keyboard(),
    )


def handle_admin_post_movie(chat_id, user, message_obj):
    if not is_admin(user["id"]):
        return
    user_state(user["id"])["admin_post"] = "movie"
    edit_message_text(message_obj, "🎬 <b>Post Movie</b>\n\nSend the movie name now.\n\nExample:\n<code>The Batman</code>", back_admin())


def handle_admin_post_tv(chat_id, user, message_obj):
    if not is_admin(user["id"]):
        return
    user_state(user["id"])["admin_post"] = "tv"
    edit_message_text(message_obj, "📺 <b>Post TV Show</b>\n\nSend the TV show name now.\n\nExample:\n<code>Breaking Bad</code>", back_admin())


def handle_admin_post_menu(chat_id, user, message_obj):
    if not is_admin(user["id"]):
        return
    edit_message_text(message_obj, "📢 <b>Post Content</b>\n\nChoose what you want to post.", admin_post_menu())


def handle_admin_text(chat_id, user, text):
    if not is_admin(user["id"]):
        return
    post_type = user_state(user["id"]).get("admin_post")
    if not post_type:
        return
    search_query = text.strip()
    if not search_query:
        return
    endpoint = "/search/movie" if post_type == "movie" else "/search/tv"
    data = tmdb_get(endpoint, {"query": search_query, "page": 1})
    results = [x for x in data.get("results", []) if x.get("id")][:10]
    if not results:
        send_message(chat_id, "❌ Nothing found. Try another name.")
        return
    user_state(user["id"])["admin_search_type"] = post_type
    keyboard = []
    for item in results:
        item_title = get_title(item)
        if len(item_title) > 30:
            item_title = item_title[:27] + "..."
        keyboard.append([inline_button(f"📌 {item_title} ({get_year(item)})", f"admin_select_{post_type}_{item['id']}")])
    keyboard.append([inline_button("🔙 Back", "admin_home")])
    send_message(chat_id, "🔎 <b>Select what to post:</b>", markups_keyboard(keyboard))


def handle_admin_select(messages, user, data):
    if not is_admin(user["id"]):
        return
    parts = data.split("_")
    if len(parts) != 4:
        return
    media_type = parts[2]
    try:
        item_id = int(parts[3])
    except ValueError:
        return
    if media_type not in ("movie", "tv"):
        return
    endpoint = f"/movie/{item_id}" if media_type == "movie" else f"/tv/{item_id}"
    item = tmdb_get(endpoint)
    send_channel_post(item, media_type)
    user_state(user["id"]).pop("admin_post", None)
    edit_message_text(messages, "✅ <b>Posted successfully!</b>", back_admin())


def handle_admin_horror(messages, user):
    if not is_admin(user["id"]):
        return
    results = []
    for page in range(1, 4):
        data = tmdb_get("/discover/tv", {"with_genres": "27", "sort_by": "popularity.desc", "vote_count.gte": 20, "page": page})
        results.extend(data.get("results", []))
    results = [x for x in results if x.get("id") and x.get("name")]
    unique = {}
    for item in results:
        unique[item["id"]] = item
    results = list(unique.values())[:3]
    if len(results) < 3:
        fallback = tmdb_get("/tv/popular", {"page": 1})
        for item in fallback.get("results", []):
            try:
                item_id = item.get("id")
                if not item_id:
                    continue
                details = tmdb_get(f"/tv/{item_id}")
                genres = [g.get("id") for g in details.get("genres", [])]
                if 27 in genres:
                    unique[item_id] = details
            except Exception:
                continue
            if len(unique) >= 3:
                break
        results = list(unique.values())[:3]
    if not results:
        edit_message_text(messages, "❌ No horror shows found right now.", back_admin())
        return
    edit_message_text(messages, f"👻 <b>Posting {len(results)} Horror Shows...</b>")
    posted = 0
    for item in results:
        try:
            send_channel_post(item, "tv")
            posted += 1
        except Exception:
            continue
    try:
        send_message(user["id"], f"✅ <b>{posted} horror shows posted successfully!</b>", back_admin())
    except Exception:
        pass


def handle_message(message):
    user = message.get("from") or {}
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")
    if not chat_id:
        return
    if user:
        save_user(user)

    if is_admin(user.get("id")) and text and not text.startswith("/"):
        try:
            handle_admin_text(chat_id, user, text)
            return
        except Exception:
            pass

    if not text:
        return

    parts = text.split(None, 1)
    command = parts[0].split("@")[0].lstrip("/").lower()
    args = parts[1].strip() if len(parts) > 1 else ""

    try:
        if command == "start":
            handle_start(chat_id, user)
        elif command == "help":
            handle_help(chat_id)
        elif command == "movie" and args:
            handle_movie_search(chat_id, user, args)
        elif command == "tvshow" and args:
            handle_tvshow_search(chat_id, user, args)
        elif command == "seasons" and args:
            handle_seasons(chat_id, user, args)
        elif command == "popular":
            handle_popular(chat_id)
        elif command == "toprated":
            handle_toprated(chat_id)
        elif command == "admin":
            handle_admin_command(chat_id, user)
    except RuntimeError as exc:
        try:
            send_message(chat_id, "❌ Error:\n<code>" + html.escape(str(exc)) + "</code>")
        except Exception:
            pass
    except Exception as exc:
        try:
            send_message(chat_id, "❌ Error:\n<code>" + html.escape(str(exc)) + "</code>")
        except Exception:
            pass


def handle_callback(callback_query):
    callback_id = callback_query.get("id")
    data = callback_query.get("data", "")
    message = callback_query.get("message") or {}
    user = callback_query.get("from") or {}
    chat_id = message.get("chat", {}).get("id")

    try:
        answer_callback(callback_id)
    except Exception:
        pass

    if user:
        save_user(user)

    try:
        if data == "check_membership":
            handle_membership(message, user)
        elif data == "results_cancel":
            handle_search_cancel(message)
        elif data == "seasons_back":
            handle_seasons_back(message)
        elif data.startswith("select_"):
            handle_select(message, callback_id, user, data)
        elif data.startswith("results_"):
            handle_results_page(message, data)
        elif data.startswith("season_show_"):
            handle_season_show(message, data)
        elif data.startswith("season_"):
            handle_season(message, data)
        elif data.startswith("episode_"):
            handle_episode(message, data)
        elif data.startswith("back_episodes_"):
            handle_back_episodes(message, data)
        elif data.startswith("back_seasons_"):
            handle_back_seasons(message, data)
        elif data.startswith("menu_"):
            handle_menu(chat_id, data)
        elif data.startswith("support"):
            handle_support(chat_id, data)
        elif data == "admin_home":
            handle_admin_home(chat_id, user, message)
        elif data == "admin_maintenance":
            handle_admin_maintenance(chat_id, user, message)
        elif data == "admin_stats":
            handle_admin_stats(chat_id, user, message)
        elif data == "admin_users":
            handle_admin_users(chat_id, user, message)
        elif data == "admin_id":
            handle_admin_id(chat_id, user, message)
        elif data == "admin_channel":
            handle_admin_channel(chat_id, user, message)
        elif data == "admin_post_movie":
            handle_admin_post_movie(chat_id, user, message)
        elif data == "admin_post_tv":
            handle_admin_post_tv(chat_id, user, message)
        elif data == "admin_post_menu":
            handle_admin_post_menu(chat_id, user, message)
        elif data == "admin_horror":
            handle_admin_horror(message, user)
        elif data.startswith("admin_select_"):
            handle_admin_select(message, user, data)
    except RuntimeError as exc:
        try:
            send_message(chat_id, "❌ Error:\n<code>" + html.escape(str(exc)) + "</code>")
        except Exception:
            pass
    except Exception as exc:
        try:
            send_message(chat_id, "❌ Error:\n<code>" + html.escape(str(exc)) + "</code>")
        except Exception:
            pass


def dispatch(update):
    if "message" in update and update.get("message", {}).get("text"):
        handle_message(update["message"])
    elif "callback_query" in update:
        handle_callback(update["callback_query"])


@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return jsonify(ok=True, botConfigured=bool(BOT_TOKEN), message="MovieBot webhook is live")

    if request.headers.get("Content-Type", "").startswith("application/json"):
        update = request.get_json(silent=True) or {}
    else:
        return jsonify(ok=False, error="Expected JSON"), 400

    if WEBHOOK_SECRET:
        provided = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if provided != WEBHOOK_SECRET:
            return jsonify(ok=False, error="Invalid secret token"), 401

    load_state()
    try:
        dispatch(update)
    except Exception:
        pass
    return jsonify(ok=True)


@app.route("/api/webhook", methods=["GET", "POST"])
def webhook_aliased():
    return webhook()


def admin_cookie_value():
    return _hmac.new(ADMIN_PASSWORD.encode(), b"moviebot-admin", hashlib.sha256).hexdigest()


def read_cookie(name):
    raw = request.headers.get("Cookie", "") or ""
    for part in raw.split(";"):
        key, _, value = part.strip().partition("=")
        if key == name:
            return value
    return ""


def admin_authed():
    if not ADMIN_PASSWORD:
        return False
    return compare_digest(read_cookie("mb_admin"), admin_cookie_value())


@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    body = request.get_json(silent=True) or {}
    password = str(body.get("password") or "")
    if not ADMIN_PASSWORD or not compare_digest(password, ADMIN_PASSWORD):
        return jsonify(ok=False, error="Invalid password"), 401
    resp = jsonify(ok=True)
    resp.set_cookie(
        "mb_admin",
        admin_cookie_value(),
        httponly=True,
        samesite="Lax",
        secure=True,
        max_age=60 * 60 * 24 * 7,
        path="/",
    )
    return resp


@app.route("/api/admin/users", methods=["GET"])
def admin_users():
    if not admin_authed():
        return jsonify(ok=False, error="Not authorized"), 401
    load_state()
    return jsonify(ok=True, users=list_all_users())


@app.route("/api/admin/send", methods=["POST"])
def admin_send():
    if not admin_authed():
        return jsonify(ok=False, error="Not authorized"), 401
    body = request.get_json(silent=True) or {}
    chat_id = str(body.get("userId") or body.get("chatId") or "").strip()
    text = str(body.get("text") or "").strip()
    if not chat_id:
        return jsonify(ok=False, error="User ID is required"), 400
    if not text:
        return jsonify(ok=False, error="Message text is required"), 400
    if len(text) > 4096:
        return jsonify(ok=False, error="Message too long (max 4096)"), 400
    try:
        send_message(chat_id, f"💬 MovieBot Support\n\n{text}")
        return jsonify(ok=True)
    except Exception as exc:
        return jsonify(ok=False, error=str(exc)), 400


ADMIN_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MovieBot Admin</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;background:#0b0e14;color:#e6e6e6;min-height:100vh;padding:32px 16px}
.wrap{max-width:980px;margin:0 auto}
h1{font-size:24px;margin-bottom:24px}
.card{background:#131a24;border:1px solid #233043;border-radius:14px;padding:20px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
@media(max-width:720px){.grid{grid-template-columns:1fr}}
input,textarea,button{width:100%;margin-top:8px;padding:10px 12px;border-radius:8px;border:1px solid #2c3a4f;background:#0b0e14;color:#e6e6e6;font-size:14px}
button{background:#22c55e;color:#06220f;font-weight:700;border:none;cursor:pointer}
button:disabled{opacity:.5}
label{font-size:12px;color:#93a4b8}
.row{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
.user{width:100%;text-align:left;border:1px solid #1e293b;background:#0e1520;margin-top:8px;cursor:pointer}
.user b{display:block;font-size:14px}
.user span{display:block;font-size:12px;color:#93a4b8}
ul{list-style:none;max-height:540px;overflow:auto}
.msg{font-size:13px;margin-top:10px}
.ok{color:#22c55e}.err{color:#f87171}
</style>
</head>
<body>
<div class="wrap">
<h1>🎬 MovieBot Admin</h1>
<div id="app"></div>
</div>
<script>
const app=document.getElementById('app');
async function j(res){const d=await res.json().catch(()=>({}));return {res,d};}
function esc(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
async function load(){
  const {res,d}=await j(await fetch('/api/admin/users'));
  if(res.status===401){return login();}
  if(!d.ok)return login();
  const users=d.users||[];
  render(`
    <div class="row"><h2 style="margin:0">Bot Users (${users.length})</h2>
    <button style="width:auto" onclick="load()">Refresh</button></div>
    <div class="grid">
      <div class="card">
        <ul>${users.length===0?'<li>No users yet.</li>':users.map(u=>`
          <li><button class="user" onclick="pick(${u.id})">
            <b>${esc(u.first_name||u.username||u.id)} ${u.username?('<span>@'+esc(u.username)+'</span>'):''}</b>
            <span>ID: ${u.id} &middot; Last seen: ${new Date((u.last_seen||'').replace(' ','T')).toLocaleString()}</span>
          </button></li>`).join('')}
        </ul>
      </div>
      <div class="card">
        <label>User / Chat ID</label>
        <input id="uid" placeholder="Tap a user on the left">
        <label>Message</label>
        <textarea id="body" rows="6" placeholder="Type your message..."></textarea>
        <button onclick="send()">Send</button>
        <div id="out" class="msg"></div>
      </div>
    </div>`);
  window.pick=id=>{document.getElementById('uid').value=id;};
  window.send=async()=>{
    const uid=document.getElementById('uid').value.trim();
    const body=document.getElementById('body').value.trim();
    const out=document.getElementById('out');
    if(!uid||!body)return;
    const {d}=await j(await fetch('/api/admin/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({userId:uid,text:body})}));
    out.className='msg '+(d.ok?'ok':'err');
    out.textContent=d.ok?'Message sent.':(d.error||'Failed');
    if(d.ok)document.getElementById('body').value='';
  };
}
function login(){
  render(`
    <div class="card" style="max-width:360px;margin:0 auto">
      <label>Admin password</label>
      <input id="pw" type="password" placeholder="••••••••">
      <button onclick="doLogin()">Sign in</button>
      <div id="out" class="msg err"></div>
    </div>`);
  window.doLogin=async()=>{
    const {d}=await j(await fetch('/api/admin/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:document.getElementById('pw').value})}));
    const out=document.getElementById('out');
    if(!d.ok){out.textContent=d.error||'Login failed';}
    else{load();}
  };
}
function render(h){app.innerHTML=h;}
load();
</script>
</body>
</html>"""


@app.route("/admin", methods=["GET"])
def admin_page():
    return ADMIN_PAGE