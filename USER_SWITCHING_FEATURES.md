# User Switching and Performance Tracking Features

## Overview
Implemented a comprehensive user switching system with performance tracking that measures the time between user login and first laser fire. This helps identify which users are most efficient at getting started with their work.

## Features Implemented

### 1. User Session Management (models.py)
- **UserSession Model**: New database table to track user sessions
  - `user_id`: Links to the User table
  - `login_time`: When the user logged in
  - `logout_time`: When the user logged out
  - `first_fire_time`: When the user first fired the laser
  - `login_method`: How they logged in (rfid, web, auto_switch)
  - `switched_from_user_id`: If this was a user switch, who was the previous user
  - `session_fire_count`: Number of fires in this session
  - `session_fire_time_ms`: Total fire time in this session
  - `performance_score`: Time from login to first fire (lower is better)
  - `machine_id`: Which machine they used
  - `card_id`: RFID card used (if applicable)

### 2. User Switching Logic (rfid_control.py)
- **Automatic User Detection**: When a different RFID card is scanned:
  - Automatically logs out the current user
  - Logs in the new user without interrupting the session
  - Creates a new user session marked as 'auto_switch'
  - Tracks which user was switched from

- **Session Management Methods**:
  - `_create_user_session()`: Creates new session and closes existing one
  - `_close_user_session()`: Properly closes session with logout time
  - `record_first_fire()`: Records first laser fire for performance tracking
  - `update_session_stats()`: Updates session statistics

### 3. Performance Tracking Integration (app.py)
- **First Fire Detection**: Added to all fire routes:
  - `/fire` (regular fire)
  - `/fire_fiber` (fiber fire sequence)
  - Automatically calls `rfid_controller.record_first_fire()` on first fire

### 4. API Endpoints for Performance Data (app.py)
- **`/api/sessions/current`**: Get current user session information
- **`/api/sessions/performance`**: Get performance statistics for all users (last 30 days)
- **`/api/sessions/user/<username>`**: Get session history for a specific user

### 5. Performance Dashboard (templates/performance.html)
- **Current Session Display**: Shows active user and their performance
- **Performance Leaderboard**: Ranks users by average performance (time to first fire)
- **Best Performance Today**: Highlights the fastest user
- **User Switching Activity**: Chart showing login method distribution
- **Performance Trends**: Visual representation of user performance over time
- **Real-time Updates**: Auto-refreshes every 5 seconds

### 6. Navigation Integration (templates/base.html)
- Added "Performance" menu item for admin users
- Positioned between existing menu items

## Performance Metrics

### Key Performance Indicator (KPI)
**Performance Score**: Total logged in time minus total fiber fire time
- **Lower is better** - indicates less non-productive time (more time actually firing vs. logged in)
- Calculated as: Session Duration - Total Fire Time
- Lower scores mean the user was more efficient with their logged-in time
- Higher scores indicate more non-productive time (logged in but not firing)
- Measured in seconds with precise calculation

### User Classification
- **Highly Efficient**: Score < 60 seconds (minimal non-productive time)
- **Efficient Workers**: Score 60-300 seconds (1-5 minutes non-productive time)  
- **Average Users**: Score 300-900 seconds (5-15 minutes non-productive time)
- **Needs Improvement**: Score > 900 seconds (15+ minutes non-productive time)

### Tracking Categories
1. **RFID Login**: User scanned their card for initial login
2. **Auto Switch**: User switched from another user via card scan
3. **Web Login**: User logged in through web interface

## Usage Scenarios

### Scenario 1: Normal Operation
1. John scans his RFID card → Creates session with login_method='rfid'
2. John works for 10 minutes and fires the laser for 8 minutes → Records performance_score=120 seconds (2 minutes of non-productive time)
3. John continues working → Session tracks fire count and time

### Scenario 2: User Switching
1. John is logged in and working
2. Sarah scans her card → John's session closes, Sarah's session starts with login_method='auto_switch', switched_from_user_id=John's ID
3. Sarah works for 5 minutes and fires the laser for 4 minutes total → Records performance_score=60 seconds (1 minute of non-productive time)
4. No interruption to machine operation - seamless handoff

### Scenario 3: Performance Tracking
1. Multiple users work throughout the day with frequent switching
2. Users view Performance page to see:
   - Who has the lowest performance scores (most efficient time usage)
   - Which users switch most frequently  
   - Trends in user efficiency over time
   - Session statistics and patterns

## Database Migration
The new UserSession table is automatically created when the application starts. Existing user data and functionality remain unchanged.

## Future Enhancements
- Daily/weekly performance reports
- Performance goals and achievements
- Team performance comparisons
- Integration with work order systems
- Automated performance notifications
- Machine learning for performance prediction

## Testing
- Created comprehensive test script (`test_user_switching.py`)
- Validates user switching logic
- Tests performance tracking calculations
- Simulates real-world usage scenarios

This implementation provides valuable insights into user efficiency and enables data-driven decisions about training, workflow optimization, and resource allocation.
