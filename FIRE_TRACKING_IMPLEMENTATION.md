# Fiber Fire Count Tracking Implementation

## 🎯 Overview
Enhanced the LCleaner Controller to properly track fiber fire counts and timing for user performance monitoring.

## 🔧 Changes Made

### 1. Enhanced Session Statistics Tracking (`config.py`)
- **Function**: `add_laser_fire_time(time_ms)`
- **Improvement**: Better import handling to avoid circular imports
- **Features**: 
  - Updates global statistics in machine_config.json
  - Updates user session statistics via RFID controller
  - Adds detailed logging for debugging

### 2. Improved RFID Session Management (`rfid_control.py`)
- **Function**: `record_first_fire()`
- **Change**: Uses `datetime.now()` instead of `datetime.utcnow()` for timezone consistency
- **Function**: `update_session_stats(fire_count_increment, fire_time_increment_ms)`
- **Improvements**:
  - Enhanced logging with before/after values
  - Better error handling and validation
  - Proper null handling for initial values

### 3. Enhanced Global Counter Logging (`config.py`)
- **Function**: `increment_laser_counter()`
- **Improvement**: Added detailed logging for debugging fire count increments

## 📊 Data Flow

```
Firing Operation Completed
         ↓
servo_control_gpioctrl.py: increment_laser_counter() + add_laser_fire_time()
         ↓
config.py: Updates global stats + calls rfid_controller.update_session_stats()
         ↓
rfid_control.py: Updates user_session table with fire count and timing
         ↓
Performance page displays real-time user session statistics
```

## 🗄️ Database Schema

The `user_session` table tracks:
- `session_fire_count`: Number of firing operations in this session
- `session_fire_time_ms`: Total firing time in milliseconds
- `first_fire_time`: Timestamp of first firing operation
- `performance_score`: Calculated performance metric

## 📈 Performance Tracking Features

1. **Per-Session Tracking**: Each RFID login creates a session that tracks:
   - Fire count (number of operations)
   - Fire time (total milliseconds of laser operation)
   - Performance score (time to first fire)

2. **Global Statistics**: Machine-wide counters in `machine_config.json`:
   - Total fire count across all users
   - Total fire time across all sessions

3. **Real-Time Updates**: Statistics update immediately after each firing operation

## 🧪 Testing

Use `test_fire_tracking.py` to verify:
- Session data is being recorded
- Fire counts are incrementing
- Fire times are accumulating
- Performance page shows live data

## 📝 Usage

1. User logs in with RFID card → Session created
2. User performs firing operations → Counts and timing tracked
3. User checks performance page → Real session data displayed
4. User logs out → Session closed with final statistics

## 🔍 Monitoring

Log messages to watch for:
- `"Session stats updated for {username}: fire count X → Y, fire time Ams → Bms"`
- `"Global laser fire counter incremented to X"`
- `"First fire recorded for {username} - Performance: X.XXs"`

This ensures comprehensive tracking of user fiber firing performance for monitoring and analysis.
