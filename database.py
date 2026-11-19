"""
Database layer for Mafia Game Manager.

Stores only persistent player roster data:
- Name
- Email (unique, case-insensitive)
- In-game status (1 for ON, 0 for OFF)

STRICT SECURITY NOTE:
This database NEVER stores game roles or assignment history.
Roles exist only transiently in server memory during an active game.
"""

import sqlite3
import re
from contextlib import contextmanager
from typing import List, Dict, Optional, Tuple, Generator

DB_PATH_DEFAULT = "mafia.db"

# RFC 5322 compliant simplified email regex
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def resolve_db_path(db_path: Optional[str] = None) -> str:
    """Return the specified path or fall back to DATABASE_PATH env or default."""
    if db_path:
        return db_path
    import os
    return os.getenv("DATABASE_PATH", DB_PATH_DEFAULT)


@contextmanager
def get_db_connection(db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite connections that guarantees conn.close()."""
    target = resolve_db_path(db_path)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize the SQLite database with the players table."""
    with get_db_connection(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                in_game INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()


def validate_player_input(name: str, email: str) -> Tuple[str, str]:
    """
    Validate and sanitize player name and email.
    Raises ValueError with a user-friendly message if invalid.
    """
    clean_name = (name or "").strip()
    clean_email = (email or "").strip().lower()

    if not clean_name:
        raise ValueError("Player name cannot be empty.")
    if len(clean_name) > 60:
        raise ValueError("Player name is too long (maximum 60 characters).")

    if not clean_email:
        raise ValueError("Email address cannot be empty.")
    if not EMAIL_REGEX.match(clean_email):
        raise ValueError(f"Invalid email format: '{clean_email}'.")

    return clean_name, clean_email


def add_player(name: str, email: str, in_game: bool = True, db_path: Optional[str] = None) -> Dict:
    """
    Add a new player to the database.
    Raises ValueError on invalid format or duplicate email.
    """
    clean_name, clean_email = validate_player_input(name, email)

    with get_db_connection(db_path) as conn:
        # Check for existing duplicate email (case-insensitive)
        cur = conn.execute("SELECT id, name FROM players WHERE email = ? COLLATE NOCASE", (clean_email,))
        existing = cur.fetchone()
        if existing:
            raise ValueError(f"A player with email '{clean_email}' already exists ({existing['name']}).")

        cursor = conn.execute(
            "INSERT INTO players (name, email, in_game) VALUES (?, ?, ?)",
            (clean_name, clean_email, 1 if in_game else 0)
        )
        conn.commit()
        new_id = cursor.lastrowid

    return {
        "id": new_id,
        "name": clean_name,
        "email": clean_email,
        "in_game": bool(in_game)
    }


def get_all_players(db_path: Optional[str] = None) -> List[Dict]:
    """Retrieve all saved players, ordered by name."""
    with get_db_connection(db_path) as conn:
        rows = conn.execute("SELECT id, name, email, in_game FROM players ORDER BY name ASC").fetchall()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "email": row["email"],
                "in_game": bool(row["in_game"])
            }
            for row in rows
        ]


def get_active_players(db_path: Optional[str] = None) -> List[Dict]:
    """Retrieve only players marked 'in_game' (ON)."""
    with get_db_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT id, name, email, in_game FROM players WHERE in_game = 1 ORDER BY name ASC"
        ).fetchall()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "email": row["email"],
                "in_game": True
            }
            for row in rows
        ]


def toggle_player_status(player_id: int, in_game: bool, db_path: Optional[str] = None) -> bool:
    """Toggle a player's in_game status. Returns True if updated."""
    with get_db_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE players SET in_game = ? WHERE id = ?",
            (1 if in_game else 0, player_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def set_all_players_status(in_game: bool, db_path: Optional[str] = None) -> int:
    """Bulk update all players to in_game=True or False. Returns affected rows."""
    with get_db_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE players SET in_game = ?",
            (1 if in_game else 0,)
        )
        conn.commit()
        return cursor.rowcount


def delete_player(player_id: int, db_path: Optional[str] = None) -> bool:
    """Delete a player by ID. Returns True if deleted."""
    with get_db_connection(db_path) as conn:
        cursor = conn.execute("DELETE FROM players WHERE id = ?", (player_id,))
        conn.commit()
        return cursor.rowcount > 0
