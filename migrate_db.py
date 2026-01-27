#!/usr/bin/env python3
"""
Migration script to add missing columns to the matches table.
This script safely adds columns that may be missing from an existing database.
"""
from sqlalchemy import text, inspect
from app.db.database import engine

def migrate():
    """Add missing columns to matches table if they don't exist."""
    inspector = inspect(engine)
    existing_columns = {col['name'] for col in inspector.get_columns('matches')}
    
    required_columns = {
        'player1_health': 'INTEGER NOT NULL DEFAULT 100',
        'player2_health': 'INTEGER NOT NULL DEFAULT 100',
        'current_turn': 'INTEGER REFERENCES users(id)',
        'turn_number': 'INTEGER NOT NULL DEFAULT 0',
        'player1_defending': 'BOOLEAN NOT NULL DEFAULT 0',
        'player2_defending': 'BOOLEAN NOT NULL DEFAULT 0',
        'player1_ability_effect': 'VARCHAR(50)',
        'player2_ability_effect': 'VARCHAR(50)',
    }
    
    with engine.connect() as conn:
        for col_name, col_def in required_columns.items():
            if col_name not in existing_columns:
                print(f"Adding column: {col_name}")
                try:
                    conn.execute(text(f"ALTER TABLE matches ADD COLUMN {col_name} {col_def}"))
                    conn.commit()
                    print(f"  ✓ Added {col_name}")
                except Exception as e:
                    print(f"  ✗ Error adding {col_name}: {e}")
            else:
                print(f"  - Column {col_name} already exists")
    
    print("\nMigration complete!")

if __name__ == "__main__":
    migrate()
