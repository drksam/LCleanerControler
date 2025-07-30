#!/usr/bin/env python3
"""Debug timezone and performance issues"""

from datetime import datetime
import time

print("🕐 Timezone Debug Information")
print("=" * 40)

# Show current times in different formats
now_utc = datetime.utcnow()
now_local = datetime.now()

print(f"Current UTC time:   {now_utc}")
print(f"Current local time: {now_local}")
print(f"Time difference:    {(now_local - now_utc).total_seconds() / 3600:.1f} hours")

# Show what JavaScript Date() would do
utc_iso = now_utc.isoformat()
print(f"\nISO string from UTC: {utc_iso}")
print("JavaScript will convert this to local time automatically")

# Show timezone info
import time
print(f"\nSystem timezone: {time.tzname}")
if time.daylight:
    print(f"Daylight saving time: {time.tzname[1]} (UTC{time.timezone/-3600:+.0f})")
else:
    print(f"Standard time: {time.tzname[0]} (UTC{time.timezone/-3600:+.0f})")

print(f"\nExpected behavior:")
print(f"  - Server stores: {now_utc} (UTC)")
print(f"  - Browser shows: {now_local} (Local)")
print(f"  - If showing 4 hours off, check server timezone settings")

print(f"\n🧪 Test Performance Calculation:")
print("For an active session:")
print("1. login_time = stored in UTC")
print("2. current_time = datetime.utcnow()")  
print("3. session_duration = current_time - login_time")
print("4. live_performance = session_duration - fire_time")
print("5. Result should update in real-time as user fires")
