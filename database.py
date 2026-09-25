"""
database.py - everything related to the SQLite database.

- get_db()        returns a database connection for the current request
- close_db()      closes that connection when the request is finished
- create_tables() creates all tables (safe to run many times)
"""

import os
import sqlite3

from flask import g

# The database file lives next to this Python file: recipe/database.db
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "database.db")


# ------------------------------------------------------------------
# Table definitions
# "IF NOT EXISTS" means running this again never deletes existing data.
# ------------------------------------------------------------------
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    email       TEXT    NOT NULL UNIQUE,
    password    TEXT    NOT NULL,              -- a hash, never the real password
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recipes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    title         TEXT    NOT NULL,
    description   TEXT    NOT NULL,
    ingredients   TEXT    NOT NULL,            -- one ingredient per line
    instructions  TEXT    NOT NULL,            -- one step per line
    category      TEXT    NOT NULL,
    difficulty    TEXT    NOT NULL CHECK (difficulty IN ('Easy', 'Medium', 'Hard')),
    prep_time     INTEGER NOT NULL CHECK (prep_time >= 0),   -- minutes
    cook_time     INTEGER NOT NULL CHECK (cook_time >= 0),   -- minutes
    servings      INTEGER NOT NULL CHECK (servings >= 1),
    image         TEXT,                        -- only the file name, e.g. "a1b2c3.jpg"
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS favorites (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    recipe_id   INTEGER NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)   REFERENCES users (id)   ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes (id) ON DELETE CASCADE,
    UNIQUE (user_id, recipe_id)                -- no duplicate favorites
);

CREATE TABLE IF NOT EXISTS reviews (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    recipe_id   INTEGER NOT NULL,
    comment     TEXT    NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)   REFERENCES users (id)   ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes (id) ON DELETE CASCADE,
    UNIQUE (user_id, recipe_id)                -- one review per user per recipe
);

CREATE TABLE IF NOT EXISTS ratings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    recipe_id   INTEGER NOT NULL,
    rating      INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)   REFERENCES users (id)   ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes (id) ON DELETE CASCADE,
    UNIQUE (user_id, recipe_id)                -- one rating per user per recipe
);
"""


def connect():
    """Open a new connection with the settings we always want."""
    connection = sqlite3.connect(DATABASE_PATH)
    # Rows behave like dictionaries: row["title"] instead of row[3]
    connection.row_factory = sqlite3.Row
    # SQLite ignores foreign keys unless we switch them on for each connection
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def get_db():
    """
    Return the database connection for the current request.
    Flask's "g" object stores it so we open at most one connection per request.
    """
    if "db" not in g:
        g.db = connect()
    return g.db


def close_db(error=None):
    """Close the connection at the end of the request (registered in app.py)."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def create_tables():
    """Create every table if it does not exist yet. Existing data is kept."""
    connection = connect()
    connection.executescript(SCHEMA_SQL)
    connection.commit()
    connection.close()
