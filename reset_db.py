#!/usr/bin/env python3
"""
Reset script to wipe all users and matches from the database.
This is a dev/prototype reset to avoid legacy data issues.

This script will:
1. Delete the SQLite database file completely (preferred for dev)
2. Recreate tables using Alembic migrations or create_all
"""
import os
from pathlib import Path
from sqlalchemy import text
from app.db.database import engine, Base, SQLALCHEMY_DATABASE_URL
from app.db import models

def reset_database():
    """Wipe all users and matches from the database by deleting the file."""
    print("Resetting database...")
    
    # Extract the database file path from SQLite URL
    # SQLite URL format: "sqlite:///./pvp_arena.db" -> "./pvp_arena.db"
    db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "")
    
    # Handle relative paths
    if db_path.startswith("./"):
        db_path = db_path[2:]
    
    db_file = Path(db_path)
    
    # Close all connections first
    engine.dispose()
    
    # Delete the database file if it exists
    if db_file.exists():
        try:
            db_file.unlink()
            print(f"  ✓ Deleted database file: {db_path}")
        except Exception as e:
            print(f"  ✗ Error deleting database file: {e}")
            print("  Falling back to table truncation...")
            # Fallback: truncate tables
            with engine.connect() as conn:
                conn.execute(text("PRAGMA foreign_keys = OFF"))
                conn.execute(text("DELETE FROM matches"))
                conn.execute(text("DELETE FROM users"))
                conn.execute(text("PRAGMA foreign_keys = ON"))
                conn.commit()
            print("  ✓ Truncated all tables")
    else:
        print(f"  - Database file not found: {db_path} (will be created on next startup)")
    
    # Recreate tables
    print("\nRecreating database tables...")
    Base.metadata.create_all(bind=engine)
    print("  ✓ Tables recreated")
    
    print("\nDatabase reset complete!")
    print("All users and matches have been wiped.")
    print("The database is now clean and ready for new data.")

if __name__ == "__main__":
    reset_database()
