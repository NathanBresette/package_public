#!/usr/bin/env python3
"""
Database migration script to add input/output token columns to existing databases.
This ensures that existing deployments get the new schema columns.
"""

import sqlite3
import os
from datetime import datetime

def migrate_database(db_file="users.db"):
    """Migrate database to include new input/output token columns"""
    print(f"Starting database migration for {db_file}")
    
    if not os.path.exists(db_file):
        print(f"Database file {db_file} does not exist. Creating new database with full schema.")
        return
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    try:
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("Users table does not exist. Creating new database with full schema.")
            return
        
        # Check if usage_records table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usage_records'")
        if not cursor.fetchone():
            print("Usage_records table does not exist. Creating new database with full schema.")
            return
        
        # Get current schema information
        cursor.execute("PRAGMA table_info(users)")
        users_columns = [col[1] for col in cursor.fetchall()]
        print(f"Current users table columns: {users_columns}")
        
        cursor.execute("PRAGMA table_info(usage_records)")
        usage_columns = [col[1] for col in cursor.fetchall()]
        print(f"Current usage_records table columns: {usage_columns}")
        
        # Add missing columns to users table
        if 'total_input_tokens' not in users_columns:
            print("Adding total_input_tokens column to users table...")
            cursor.execute('ALTER TABLE users ADD COLUMN total_input_tokens INTEGER DEFAULT 0')
            print("✓ Added total_input_tokens column")
        else:
            print("✓ total_input_tokens column already exists")
            
        if 'total_output_tokens' not in users_columns:
            print("Adding total_output_tokens column to users table...")
            cursor.execute('ALTER TABLE users ADD COLUMN total_output_tokens INTEGER DEFAULT 0')
            print("✓ Added total_output_tokens column")
        else:
            print("✓ total_output_tokens column already exists")
        
        # Add missing columns to usage_records table
        if 'input_tokens' not in usage_columns:
            print("Adding input_tokens column to usage_records table...")
            cursor.execute('ALTER TABLE usage_records ADD COLUMN input_tokens INTEGER DEFAULT 0')
            print("✓ Added input_tokens column")
        else:
            print("✓ input_tokens column already exists")
            
        if 'output_tokens' not in usage_columns:
            print("Adding output_tokens column to usage_records table...")
            cursor.execute('ALTER TABLE usage_records ADD COLUMN output_tokens INTEGER DEFAULT 0')
            print("✓ Added output_tokens column")
        else:
            print("✓ output_tokens column already exists")
        
        # Update existing records to have default values for new columns
        print("Updating existing records with default values...")
        
        # Update users table - set total_input_tokens and total_output_tokens to 0 if NULL
        cursor.execute('''
            UPDATE users 
            SET total_input_tokens = COALESCE(total_input_tokens, 0),
                total_output_tokens = COALESCE(total_output_tokens, 0)
            WHERE total_input_tokens IS NULL OR total_output_tokens IS NULL
        ''')
        users_updated = cursor.rowcount
        print(f"✓ Updated {users_updated} user records")
        
        # Update usage_records table - set input_tokens and output_tokens to 0 if NULL
        cursor.execute('''
            UPDATE usage_records 
            SET input_tokens = COALESCE(input_tokens, 0),
                output_tokens = COALESCE(output_tokens, 0)
            WHERE input_tokens IS NULL OR output_tokens IS NULL
        ''')
        usage_updated = cursor.rowcount
        print(f"✓ Updated {usage_updated} usage records")
        
        # Create indexes if they don't exist
        print("Creating indexes...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_access_code ON users(access_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_access_code ON usage_records(access_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_records(timestamp)')
        print("✓ Created indexes")
        
        # Commit changes
        conn.commit()
        print("✓ Database migration completed successfully!")
        
        # Show final schema
        print("\nFinal schema:")
        cursor.execute("PRAGMA table_info(users)")
        users_columns = [col[1] for col in cursor.fetchall()]
        print(f"Users table columns: {users_columns}")
        
        cursor.execute("PRAGMA table_info(usage_records)")
        usage_columns = [col[1] for col in cursor.fetchall()]
        print(f"Usage_records table columns: {usage_columns}")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    # Check if we're in the backend directory
    if os.path.exists("users.db"):
        migrate_database("users.db")
    elif os.path.exists("backend/users.db"):
        migrate_database("backend/users.db")
    else:
        print("No database file found. Creating new database with full schema.")
        print("The database will be created automatically when the application starts.") 