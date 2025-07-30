#!/usr/bin/env python3
"""
Database Migration Script
-------------------------

Helps migrate the local SQLite database to a remote server when ready.
Supports export to SQL dump for easy import into PostgreSQL, MySQL, etc.
"""

import os
import sqlite3
import json
from datetime import datetime
from pathlib import Path

def export_database_to_sql(db_path, output_file=None):
    """Export SQLite database to SQL dump file"""
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return None
    
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'LCleaner_export_{timestamp}.sql'
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Get database dump
        with open(output_file, 'w') as f:
            # Write header
            f.write(f"-- LCleaner Database Export\n")
            f.write(f"-- Generated: {datetime.now().isoformat()}\n")
            f.write(f"-- Source: {db_path}\n\n")
            
            # Dump schema and data
            for line in conn.iterdump():
                f.write(f"{line}\n")
        
        conn.close()
        
        file_size = os.path.getsize(output_file)
        print(f"✅ Database exported to: {output_file}")
        print(f"📊 Export size: {file_size} bytes")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return None

def generate_migration_info(db_path):
    """Generate migration information and statistics"""
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("📊 Database Migration Information")
        print("=" * 40)
        
        # Get table statistics
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        total_records = 0
        for table in sorted(tables):
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            total_records += count
            print(f"  {table}: {count} records")
        
        print(f"\nTotal records: {total_records}")
        
        # Database file size
        file_size = os.path.getsize(db_path)
        print(f"Database size: {file_size} bytes ({file_size/1024:.1f} KB)")
        
        # Session statistics
        cursor.execute("SELECT COUNT(*) FROM user_session")
        session_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_session WHERE logout_time IS NULL")
        active_sessions = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(session_fire_count) FROM user_session")
        total_fires = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(session_fire_time_ms) FROM user_session")
        total_fire_time_ms = cursor.fetchone()[0] or 0
        
        print(f"\n🔥 Performance Data:")
        print(f"  Total sessions: {session_count}")
        print(f"  Active sessions: {active_sessions}")
        print(f"  Total fires: {total_fires}")
        print(f"  Total fire time: {total_fire_time_ms/1000:.1f} seconds")
        
        # User statistics
        cursor.execute("SELECT COUNT(*) FROM user")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM rfid_card")
        rfid_count = cursor.fetchone()[0]
        
        print(f"\n👥 User Data:")
        print(f"  Users: {user_count}")
        print(f"  RFID Cards: {rfid_count}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error analyzing database: {e}")

def create_migration_package():
    """Create a complete migration package"""
    
    db_path = 'instance/LCleaner_production.db'
    
    print("📦 Creating Migration Package")
    print("=" * 40)
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    # Create migration directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    migration_dir = Path(f'migration_{timestamp}')
    migration_dir.mkdir(exist_ok=True)
    
    # Copy database file
    import shutil
    db_copy = migration_dir / 'LCleaner_production.db'
    shutil.copy2(db_path, db_copy)
    print(f"✅ Database copied: {db_copy}")
    
    # Export SQL dump
    sql_file = migration_dir / 'LCleaner_export.sql'
    export_database_to_sql(db_path, str(sql_file))
    
    # Create migration instructions
    instructions_file = migration_dir / 'MIGRATION_INSTRUCTIONS.md'
    create_migration_instructions(str(instructions_file), str(db_copy), str(sql_file))
    
    # Create configuration template
    config_file = migration_dir / 'remote_database_config.json'
    create_remote_config_template(str(config_file))
    
    print(f"\n🎉 Migration package created: {migration_dir}")
    print(f"📁 Contents:")
    for item in migration_dir.iterdir():
        size = item.stat().st_size
        print(f"  • {item.name}: {size} bytes")

def create_migration_instructions(instructions_file, db_file, sql_file):
    """Create migration instructions file"""
    
    instructions = f"""# LCleaner Database Migration Instructions

## Overview
This package contains the complete LCleaner database for migration to a remote server.

## Files Included
- `{Path(db_file).name}`: Complete SQLite database file
- `{Path(sql_file).name}`: SQL dump for import into other database systems
- `remote_database_config.json`: Configuration template for remote database

## Migration Options

### Option 1: PostgreSQL Migration
1. Install PostgreSQL on remote server
2. Create new database: `createdb lcleaner_production`
3. Import schema and data: `psql lcleaner_production < {Path(sql_file).name}`
4. Update application configuration with PostgreSQL connection string

### Option 2: MySQL Migration
1. Install MySQL on remote server
2. Create new database: `CREATE DATABASE lcleaner_production;`
3. Import data: `mysql lcleaner_production < {Path(sql_file).name}`
4. Update application configuration with MySQL connection string

### Option 3: Copy SQLite Database
1. Copy `{Path(db_file).name}` to remote server
2. Update `DATABASE_URL` in application configuration
3. Ensure file permissions are correct

## Configuration Updates

Update your application configuration with the new database URL:

### PostgreSQL Example:
```
DATABASE_URL=postgresql://username:password@hostname:5432/lcleaner_production
```

### MySQL Example:
```
DATABASE_URL=mysql://username:password@hostname:3306/lcleaner_production
```

### Remote SQLite Example:
```
DATABASE_URL=sqlite:///path/to/remote/database.db
```

## Data Verification

After migration, verify:
- [ ] All users can login
- [ ] RFID cards work correctly
- [ ] Session tracking functions
- [ ] Performance data is preserved
- [ ] Fire count statistics are accurate

## Rollback Plan

Keep the original SQLite database file as backup:
- Original location: `instance/LCleaner_production.db`
- Can restore by copying back and updating configuration

Generated: {datetime.now().isoformat()}
"""
    
    with open(instructions_file, 'w') as f:
        f.write(instructions)
    
    print(f"✅ Instructions created: {instructions_file}")

def create_remote_config_template(config_file):
    """Create remote database configuration template"""
    
    config = {
        "database": {
            "type": "postgresql",  # or "mysql", "sqlite"
            "host": "your-database-server.com",
            "port": 5432,
            "database": "lcleaner_production",
            "username": "lcleaner_user",
            "password": "your-secure-password",
            "ssl_mode": "require",
            "connection_pool_size": 10,
            "backup_enabled": True,
            "backup_schedule": "daily"
        },
        "migration": {
            "source_database": "SQLite",
            "migration_date": datetime.now().isoformat(),
            "data_preserved": [
                "users",
                "rfid_cards", 
                "access_logs",
                "user_sessions",
                "performance_data"
            ]
        }
    }
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Remote config template: {config_file}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='LCleaner Database Migration Tool')
    parser.add_argument('--info', action='store_true', help='Show migration information')
    parser.add_argument('--export', action='store_true', help='Export SQL dump only')
    parser.add_argument('--package', action='store_true', help='Create complete migration package')
    
    args = parser.parse_args()
    
    db_path = 'instance/LCleaner_production.db'
    
    if args.info:
        generate_migration_info(db_path)
    elif args.export:
        export_database_to_sql(db_path)
    elif args.package:
        create_migration_package()
    else:
        print("LCleaner Database Migration Tool")
        print("Usage:")
        print("  --info     Show database information")
        print("  --export   Export SQL dump")
        print("  --package  Create migration package")

if __name__ == "__main__":
    main()
