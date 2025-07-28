#!/usr/bin/env python3
"""
Create SQLite database for user management
Replaces user_data.json with a proper database
"""

import sqlite3
import json
import os
from datetime import datetime
import hashlib

def create_users_database():
    """Create the users database with proper schema"""
    
    # Connect to database (creates it if it doesn't exist)
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            access_code TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT,
            user_name TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            is_admin BOOLEAN DEFAULT 0,
            created_at TEXT NOT NULL,
            last_activity TEXT,
            total_requests INTEGER DEFAULT 0,
            total_cost REAL DEFAULT 0.0,
            total_tokens INTEGER DEFAULT 0,
            daily_limit INTEGER DEFAULT 100,
            monthly_budget REAL DEFAULT 10.0,
            rate_limit INTEGER DEFAULT 10,
            context_count INTEGER DEFAULT 0,
            notes TEXT,
            billing_status TEXT DEFAULT 'inactive'
        )
    ''')
    
    # Create usage_records table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usage_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            access_code TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            request_type TEXT NOT NULL,
            tokens_used INTEGER DEFAULT 0,
            cost REAL DEFAULT 0.0,
            prompt_length INTEGER DEFAULT 0,
            response_length INTEGER DEFAULT 0,
            success BOOLEAN DEFAULT 1,
            error_message TEXT,
            FOREIGN KEY (access_code) REFERENCES users (access_code)
        )
    ''')
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_access_code ON users(access_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_access_code ON usage_records(access_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_records(timestamp)')
    
    conn.commit()
    conn.close()
    
    print("✅ Users database created successfully!")

def migrate_existing_data():
    """Migrate data from user_data.json to SQLite"""
    
    if not os.path.exists('user_data.json'):
        print("❌ user_data.json not found. Creating empty database.")
        return
    
    # Load existing JSON data
    with open('user_data.json', 'r') as f:
        data = json.load(f)
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Migrate users
    for access_code, user_data in data.get('users', {}).items():
        cursor.execute('''
            INSERT OR REPLACE INTO users (
                access_code, email, password_hash, user_name, is_active, is_admin,
                created_at, last_activity, total_requests, total_cost, total_tokens,
                daily_limit, monthly_budget, rate_limit, context_count, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            access_code,
            user_data.get('email', ''),
            user_data.get('password_hash', ''),  # Will be empty for existing users
            user_data.get('user_name', 'Unknown User'),
            user_data.get('is_active', True),
            user_data.get('is_admin', False),
            user_data.get('created_at', datetime.now().isoformat()),
            user_data.get('last_activity', ''),
            user_data.get('total_requests', 0),
            user_data.get('total_cost', 0.0),
            user_data.get('total_tokens', 0),
            user_data.get('daily_limit', 100),
            user_data.get('monthly_budget', 10.0),
            user_data.get('rate_limit', 10),
            user_data.get('context_count', 0),
            user_data.get('notes', '')
        ))
    
    # Migrate usage records
    for record in data.get('usage_records', []):
        cursor.execute('''
            INSERT INTO usage_records (
                access_code, timestamp, request_type, tokens_used, cost,
                prompt_length, response_length, success, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record.get('access_code', ''),
            record.get('timestamp', ''),
            record.get('request_type', ''),
            record.get('tokens_used', 0),
            record.get('cost', 0.0),
            record.get('prompt_length', 0),
            record.get('response_length', 0),
            record.get('success', True),
            record.get('error_message', '')
        ))
    
    conn.commit()
    conn.close()
    
    print("✅ Data migrated from user_data.json to SQLite!")

def verify_migration():
    """Verify the migration was successful"""
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Count users
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]
    
    # Count usage records
    cursor.execute('SELECT COUNT(*) FROM usage_records')
    usage_count = cursor.fetchone()[0]
    
    # Show sample data
    cursor.execute('SELECT access_code, email, user_name, daily_limit FROM users LIMIT 5')
    users = cursor.fetchall()
    
    conn.close()
    
    print(f"\n📊 Migration Results:")
    print(f"   Users migrated: {user_count}")
    print(f"   Usage records migrated: {usage_count}")
    print(f"\n📋 Sample users:")
    for user in users:
        print(f"   {user[0]} | {user[1]} | {user[2]} | Limit: {user[3]}")

if __name__ == "__main__":
    print("🚀 Creating SQLite users database...")
    create_users_database()
    
    print("\n📦 Migrating existing data...")
    migrate_existing_data()
    
    print("\n🔍 Verifying migration...")
    verify_migration()
    
    print("\n✅ Database setup complete!")
    print("💡 Next: Update user_management.py to use SQLite instead of JSON") 