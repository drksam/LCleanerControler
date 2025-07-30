#!/usr/bin/env python3
"""
Setup Local Production Database on Raspberry Pi
-----------------------------------------------

Creates a persistent SQLite database that can be migrated to a remote server later.
This database will persist between application restarts and contain all real data.
"""

import os
import sqlite3
import json
from datetime import datetime
from pathlib import Path

def setup_local_production_db():
    """Setup local production database on Raspberry Pi"""
    
    print("🗄️  Setting Up Local Production Database")
    print("=" * 50)
    
    # Create instance directory if it doesn't exist
    instance_dir = Path('instance')
    instance_dir.mkdir(exist_ok=True)
    print(f"✓ Instance directory created: {instance_dir.absolute()}")
    
    # Database file path
    db_path = instance_dir / 'LCleaner_production.db'
    
    print(f"📂 Database location: {db_path.absolute()}")
    
    # Create/connect to database
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if tables already exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        if existing_tables:
            print(f"✓ Database exists with {len(existing_tables)} tables:")
            for table in sorted(existing_tables):
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  • {table}: {count} records")
        else:
            print("📝 Creating new database tables...")
            
            # Create all necessary tables
            create_tables(cursor)
            
            # Create default users and RFID cards
            create_default_data(cursor)
            
            conn.commit()
            print("✓ Database tables created successfully!")
        
        # Ensure user_session table exists (our main concern)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_session';")
        if not cursor.fetchone():
            print("🔧 Creating user_session table...")
            create_user_session_table(cursor)
            conn.commit()
            print("✓ user_session table created!")
        
        conn.close()
        
        # Update configuration to use this database
        update_database_config(str(db_path.absolute()))
        
        print("\n🎉 Local production database setup complete!")
        print(f"📁 Database file: {db_path.absolute()}")
        print(f"📊 Size: {db_path.stat().st_size if db_path.exists() else 0} bytes")
        
        return str(db_path.absolute())
        
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        return None

def create_tables(cursor):
    """Create all necessary database tables"""
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(64) UNIQUE NOT NULL,
            full_name VARCHAR(100),
            email VARCHAR(120) UNIQUE,
            password_hash VARCHAR(256),
            access_level VARCHAR(20) DEFAULT 'operator',
            department VARCHAR(100),
            active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # RFID Cards table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rfid_card (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id VARCHAR(32) UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            description TEXT,
            active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user (id)
        )
    ''')
    
    # Access Log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            card_id VARCHAR(32),
            access_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            access_granted BOOLEAN,
            access_method VARCHAR(20),
            ip_address VARCHAR(45),
            user_agent TEXT,
            FOREIGN KEY (user_id) REFERENCES user (id)
        )
    ''')
    
    # User Session table (the one we need!)
    create_user_session_table(cursor)
    
    # API Keys table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_key (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            "key" VARCHAR(256) UNIQUE NOT NULL,
            description TEXT,
            active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_used DATETIME
        )
    ''')

def create_user_session_table(cursor):
    """Create the user_session table specifically"""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            login_time DATETIME NOT NULL,
            logout_time DATETIME,
            first_fire_time DATETIME,
            login_method VARCHAR(20) DEFAULT 'unknown',
            switched_from_user_id INTEGER,
            session_fire_count INTEGER DEFAULT 0,
            session_fire_time_ms BIGINT DEFAULT 0,
            performance_score FLOAT,
            machine_id VARCHAR(64),
            card_id VARCHAR(32),
            FOREIGN KEY (user_id) REFERENCES user (id),
            FOREIGN KEY (switched_from_user_id) REFERENCES user (id)
        )
    ''')
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_session_user_id ON user_session(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_session_login_time ON user_session(login_time)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_session_logout_time ON user_session(logout_time)')

def create_default_data(cursor):
    """Create default users and RFID cards"""
    
    # Create default admin user
    cursor.execute('''
        INSERT OR IGNORE INTO user (username, full_name, access_level, department)
        VALUES ('admin', 'Default Administrator', 'admin', 'System Administration')
    ''')
    
    # Create default operator user
    cursor.execute('''
        INSERT OR IGNORE INTO user (username, full_name, access_level, department)
        VALUES ('laser', 'Laser Operator', 'operator', 'Production')
    ''')
    
    # Get user IDs
    cursor.execute('SELECT id FROM user WHERE username = "admin"')
    admin_id = cursor.fetchone()[0]
    
    cursor.execute('SELECT id FROM user WHERE username = "laser"')
    laser_id = cursor.fetchone()[0]
    
    # Create default RFID cards
    cursor.execute('''
        INSERT OR IGNORE INTO rfid_card (card_id, user_id, description)
        VALUES ('2667607583', ?, 'Default Admin RFID Card')
    ''', (admin_id,))
    
    cursor.execute('''
        INSERT OR IGNORE INTO rfid_card (card_id, user_id, description)
        VALUES ('3743073564', ?, 'Default Laser RFID Card')
    ''', (laser_id,))

def update_database_config(db_path):
    """Update configuration to use the local production database"""
    try:
        # Load current config
        config_file = 'machine_config.json'
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = {}
        
        # Add database configuration
        if 'database' not in config:
            config['database'] = {}
        
        config['database']['type'] = 'sqlite'
        config['database']['path'] = db_path
        config['database']['backup_enabled'] = True
        config['database']['backup_interval_hours'] = 24
        
        # Write updated config
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✓ Configuration updated with database path")
        
        # Also set environment variable for Flask
        database_url = f"sqlite:///{db_path}"
        print(f"✓ Database URL: {database_url}")
        
        # Create a .env file for persistent environment variables
        with open('.env', 'w') as f:
            f.write(f"DATABASE_URL={database_url}\n")
            f.write("FLASK_ENV=production\n")
            f.write("FLASK_DEBUG=False\n")
        
        print("✓ Environment variables saved to .env file")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not update configuration: {e}")

def create_database_backup():
    """Create a backup of the current database"""
    db_path = Path('instance/LCleaner_production.db')
    if db_path.exists():
        backup_dir = Path('backups')
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = backup_dir / f'LCleaner_backup_{timestamp}.db'
        
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✓ Database backup created: {backup_path}")
        return str(backup_path)
    return None

def main():
    """Main entry point"""
    print("🚀 Local Production Database Setup")
    print("=" * 50)
    
    # Setup database
    db_path = setup_local_production_db()
    
    if db_path:
        print("\n📋 Next Steps:")
        print("1. Run the application:")
        print("   python main.py")
        print("   OR")
        print("   python test_run.py --production-db --hardware")
        print()
        print("2. Login with RFID card to test session tracking")
        print("3. Perform firing operations to test performance tracking")
        print("4. Check performance page for fire count data")
        print()
        print("📦 Migration Ready:")
        print(f"   Database file: {db_path}")
        print("   Can be copied to remote server when ready")
        print("   Contains all user data, sessions, and performance metrics")
        
        # Create initial backup
        backup_path = create_database_backup()
        if backup_path:
            print(f"   Initial backup: {backup_path}")
    else:
        print("❌ Database setup failed!")

if __name__ == "__main__":
    main()
