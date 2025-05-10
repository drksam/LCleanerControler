# Cross-App Database Architecture for Shop Suite Applications

## Overview

This document outlines the database architecture for the Shop Suite applications:
- **ShopMonitor** - The real-world interface that tracks machines, areas, and shop floor activities
- **ShopTracker** - The office-side application for management, planning, and reporting
- **Shared Infrastructure** - The common database and services that connect these applications

## Database Architecture

The Shop Suite uses a modular database architecture designed for shared data access across multiple applications while maintaining separation of app-specific functionality:

```
shop_suite_db
├── Core (Shared)
│   ├── Users & Authentication
│   ├── Areas & Zones
│   ├── Machines & Equipment
│   ├── Permissions & Access Control
│   └── Integration & Sync
├── ShopMonitor (App-Specific)
│   ├── Node Management
│   ├── Machine Sessions
│   ├── RFID Activities
│   └── Shop Floor Events
└── ShopTracker (App-Specific)
    ├── Orders & Jobs
    ├── Planning & Scheduling
    ├── Analytics
    └── Resource Management
```

## Deployment Model

The database can be deployed in several configurations:

1. **Single Database Server** - All schemas on one server (development/small deployments)
2. **Distributed Database** - Core on central server with app-specific DBs on separate servers
3. **Cloud-Based** - Using managed database services with appropriate connection pooling

## Core Shared Database

### 1. User Management and Single Sign-On (SSO)

```python
class SuiteUser(db.Model):
    __tablename__ = 'suite_users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    display_name = db.Column(db.String(100))
    active = db.Column(db.Boolean, default=True)
    auth_provider = db.Column(db.String(50), default="local")  # local, azure, google, etc.
    external_id = db.Column(db.String(100))  # ID in external auth system
    is_admin = db.Column(db.Boolean, default=False)
    rfid_tag = db.Column(db.String(64))  # Optional RFID association
    
    # Cross-app tracking
    created_by_app = db.Column(db.String(50))  # "shop_monitor" or "shop_tracker"
    managed_by_app = db.Column(db.String(50))  # Which app manages this user
```

### 2. Permissions System

```python
class SuitePermission(db.Model):
    __tablename__ = 'suite_permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('suite_users.id'), nullable=False)
    resource_type = db.Column(db.String(50))  # area, machine, report, etc.
    resource_id = db.Column(db.Integer)  # The ID of the resource
    app_context = db.Column(db.String(50))  # Which app this permission applies to
    permission_level = db.Column(db.String(20))  # view, edit, admin, operate, etc.
```

### 3. Session Management

```python
class UserSession(db.Model):
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('suite_users.id'), nullable=False)
    session_token = db.Column(db.String(128), unique=True, nullable=False)
    current_app = db.Column(db.String(50))  # Which app user is currently using
    expires_at = db.Column(db.DateTime, nullable=False)
```

### 4. Synchronization and Events

```python
class SyncEvent(db.Model):
    __tablename__ = 'sync_events'
    
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50))  # user.created, machine.updated, etc.
    resource_type = db.Column(db.String(50))  # user, machine, area, etc.
    resource_id = db.Column(db.Integer)
    source_app = db.Column(db.String(50))  # Which app generated this event
    target_app = db.Column(db.String(50))  # Which app should process this event
    status = db.Column(db.String(20), default="pending")  # pending, processed, failed
    payload = db.Column(db.Text)  # JSON data for the event
```

## App-Specific Data Models

### ShopMonitor Models

The existing models are maintained with references to the new shared models:

1. **Node & Hardware Management**
   - Node model with reference to shared Areas/Zones
   - AccessoryIO model for hardware I/O management
   - BluetoothDevice model for audio devices

2. **Activity Tracking**
   - MachineSession model with reference to shared User model
   - MachineLog model for historical data

3. **Alert & Safety Systems**
   - EStopEvent model
   - Alert model updated to use shared user references

### ShopTracker Models

New models for office-side functionality:

1. **Production Planning**
   - Orders
   - Jobs
   - Work Plans

2. **Resource Management**
   - Materials
   - Inventory
   - Equipment Maintenance

3. **Business Intelligence**
   - Reports
   - Analytics
   - Dashboards

## Integration Patterns

The database architecture supports these integration patterns:

1. **Shared Tables** - Core data accessed directly by both systems
2. **Event Propagation** - Changes in one app trigger events for others
3. **API Services** - Specialized access via REST APIs
4. **Message Queue** - Asynchronous processing using queues

## Scalability Features

### 1. Horizontal Scaling

The database architecture supports dividing workloads across multiple servers:
   - Read replicas for heavy query workloads
   - Sharding by region for international deployments
   - Database connection pooling for efficient resource use

### 2. Vertical Scaling

Increasing resources for the database server:
   - Memory optimization for frequently accessed data
   - Index optimization based on query patterns
   - Query cache configurations

### 3. Caching Strategy

Multi-level caching to reduce database load:
   - Redis/Memcached for frequent queries
   - Application-level caching
   - Database query result caching

## Migration Strategy

Converting from the current database to this cross-app architecture:

1. **Create Shared Schema**:
   - Set up the new shared database tables
   - Deploy the API service layer

2. **Data Migration**:
   - Migrate core data to the shared database
   - Connect existing models to shared models

3. **Application Updates**:
   - Update each app to use the shared database
   - Implement SSO system

4. **Parallel Operation**:
   - Feature flags to control functionality
   - Validate each module before proceeding

## Database Configuration

The database configuration accommodates multiple applications:

```python
# ShopMonitor Config
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", 
    "postgresql://username:password@database.server:5432/shop_suite_db"
)

# Connection pooling for multi-app access
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": 10,
    "max_overflow": 20,
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Specify schema (if using PostgreSQL schema separation)
app.config["SQLALCHEMY_BINDS"] = {
    'core': os.environ.get("CORE_DATABASE_URL", app.config["SQLALCHEMY_DATABASE_URI"]),
    'shop_monitor': os.environ.get("MONITOR_DATABASE_URL", app.config["SQLALCHEMY_DATABASE_URI"] + "?schema=shop_monitor"),
}
```

## Security Considerations

The shared database implements several security measures:

1. **Row-Level Security** - Database-enforced access controls
2. **Schema Separation** - Logical isolation of app-specific data
3. **Audit Trails** - Tracking all changes across applications
4. **Encrypted Credentials** - Sensitive data encryption
5. **Connection Firewalls** - Network-level isolation and protection

## Backup and Recovery

Comprehensive backup strategy for the shared database:

1. **Continuous Archiving** - For point-in-time recovery
2. **Daily Snapshots** - For quick restores
3. **Cross-Region Replication** - For disaster recovery
4. **Automated Testing** - Regularly validated restore process

## Performance Monitoring

The database includes instrumentation for performance monitoring:

1. **Query Performance** - Tracking slow queries across apps
2. **Connection Usage** - Monitoring connection pools
3. **Growth Metrics** - Tracking table sizes and growth rates
4. **Cross-App Impact** - Identifying how one app affects another's performance