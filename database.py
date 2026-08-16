import sqlite3
from datetime import datetime

from config import DATABASE_PATH


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    return sqlite3.connect(DATABASE_PATH)


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            joined_at TEXT,
            last_seen TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            query TEXT,
            search_type TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    conn.commit()
    conn.close()


# ============================================================
# USERS
# ============================================================

def save_user(
    user_id,
    username=None,
    first_name=None,
    last_name=None,
):
    now = datetime.utcnow().isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT user_id FROM users WHERE user_id = ?",
        (user_id,)
    )

    exists = cursor.fetchone()

    if exists:
        cursor.execute("""
            UPDATE users
            SET username = ?,
                first_name = ?,
                last_name = ?,
                last_seen = ?
            WHERE user_id = ?
        """, (
            username,
            first_name,
            last_name,
            now,
            user_id,
        ))
    else:
        cursor.execute("""
            INSERT INTO users (
                user_id,
                username,
                first_name,
                last_name,
                joined_at,
                last_seen
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            username,
            first_name,
            last_name,
            now,
            now,
        ))

    conn.commit()
    conn.close()


def get_user_count():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM users"
    )

    result = cursor.fetchone()
    conn.close()

    return result[0] if result else 0


def get_recent_users(limit=10):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            user_id,
            username,
            first_name,
            last_name,
            joined_at,
            last_seen
        FROM users
        ORDER BY joined_at DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return rows


# ============================================================
# SEARCHES
# ============================================================

def save_search(
    user_id,
    query,
    search_type,
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO searches (
            user_id,
            query,
            search_type,
            created_at
        )
        VALUES (?, ?, ?, ?)
    """, (
        user_id,
        query,
        search_type,
        datetime.utcnow().isoformat(),
    ))

    conn.commit()
    conn.close()


def get_search_count():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM searches"
    )

    result = cursor.fetchone()
    conn.close()

    return result[0] if result else 0


# ============================================================
# SETTINGS
# ============================================================

def get_setting(key, default=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT value FROM settings WHERE key = ?",
        (key,)
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        return row[0]

    return default


def set_setting(key, value):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key)
        DO UPDATE SET value = excluded.value
    """, (
        key,
        str(value),
    ))

    conn.commit()
    conn.close()


# ============================================================
# MAINTENANCE
# ============================================================

def is_maintenance():
    return get_setting(
        "maintenance",
        "0"
    ) == "1"


def set_maintenance(enabled):
    set_setting(
        "maintenance",
        "1" if enabled else "0"
    )


# ============================================================
# CHANNEL SETTINGS
# ============================================================

def get_channel_id():
    return get_setting(
        "channel_id",
        None
    )


def set_channel_id(channel_id):
    set_setting(
        "channel_id",
        channel_id
    )