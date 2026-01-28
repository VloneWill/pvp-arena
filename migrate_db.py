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
        'player1_ability_cooldown': 'INTEGER NOT NULL DEFAULT 0',
        'player2_ability_cooldown': 'INTEGER NOT NULL DEFAULT 0',
        'winner_id': 'INTEGER REFERENCES users(id)',
        'xp_awarded': 'BOOLEAN NOT NULL DEFAULT 0',
        'combat_log': 'TEXT',  # JSON stored as TEXT in SQLite
    }
    
    with engine.connect() as conn:
        for col_name, col_def in required_columns.items():
            if col_name not in existing_columns:
                print(f"Adding column to matches: {col_name}")
                try:
                    conn.execute(text(f"ALTER TABLE matches ADD COLUMN {col_name} {col_def}"))
                    conn.commit()
                    print(f"  ✓ Added {col_name}")
                except Exception as e:
                    print(f"  ✗ Error adding {col_name}: {e}")
            else:
                print(f"  - Column {col_name} already exists in matches")
        
        # Handle users table columns
        try:
            user_columns = {col['name'] for col in inspector.get_columns('users')}
            user_required_columns = {
                'class_name': 'VARCHAR(20)',
                'level': 'INTEGER NOT NULL DEFAULT 1',
                'xp': 'INTEGER NOT NULL DEFAULT 0',
            }
            
            for col_name, col_def in user_required_columns.items():
                if col_name not in user_columns:
                    print(f"Adding column to users: {col_name}")
                    try:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"))
                        conn.commit()
                        print(f"  ✓ Added {col_name} to users")
                    except Exception as e:
                        print(f"  ✗ Error adding {col_name} to users: {e}")
                else:
                    print(f"  - Column {col_name} already exists in users")
        except Exception as e:
            print(f"  Note: Could not check users table: {e}")
        
        # Initialize combat_log for existing matches if column was just added
        if 'combat_log' not in existing_columns:
            try:
                conn.execute(text("UPDATE matches SET combat_log = '[]' WHERE combat_log IS NULL"))
                conn.commit()
                print("  ✓ Initialized combat_log for existing matches")
            except Exception as e:
                print(f"  Note: Could not initialize combat_log: {e}")
    
    print("\nMigration complete!")

if __name__ == "__main__":
    migrate()
