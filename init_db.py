"""
init_db.py - create the SQLite database and its tables.

Run it once after installing the project:
    python init_db.py

It is safe to run again: existing tables and data are NOT deleted.
"""

from database import DATABASE_PATH, create_tables

if __name__ == "__main__":
    create_tables()
    print(f"Database is ready: {DATABASE_PATH}")
