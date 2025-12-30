#!/usr/bin/env python3
"""
Add name column to users table
"""
from app.database import engine
from sqlalchemy import text

def upgrade():
    """Add name column to users table"""
    with engine.connect() as conn:
        # Check if column already exists
        result = conn.execute(text("""
            SELECT COUNT(*)
            FROM pragma_table_info('users')
            WHERE name='name'
        """))

        if result.scalar() == 0:
            print("Adding 'name' column to users table...")
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN name VARCHAR(50)
            """))
            conn.commit()
            print("✅ 'name' column added successfully")
        else:
            print("ℹ️  'name' column already exists")

if __name__ == "__main__":
    upgrade()
    print("Migration completed!")
