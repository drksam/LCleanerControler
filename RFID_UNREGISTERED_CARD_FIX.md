# RFID Unregistered Card LED Fix

## Problem
Non-registered RFID cards were failing silently and not flashing the WS2812B LED RED as expected. Instead, they were showing the blue/white LOGIN_SCREEN state.

## Root Cause Analysis

### Log Evidence:
```
2025-07-30 12:18:51,162 - root - WARNING - Access denied: Card not found in local database
2025-07-30 12:18:51,163 - root - INFO - Access control callback triggered: granted=False, user_data={'reason': 'Card not found in local database'}
2025-07-30 12:18:51,163 - root - INFO - Authentication removed: Card not found in local database
2025-07-30 12:18:51,164 - ws2812b_controller - INFO - LED state set to LOGIN_SCREEN
```

### Issue #1: Incorrect Reason String Matching
**Problem:** The access control callback was only checking for `reason.lower() == "card_denied"` but the RFID controller was sending `"Card not found in local database"`.

**Fix:** Updated the condition to match multiple access denial scenarios:
```python
if (reason.lower() == "card_denied" or 
    "card not found" in reason.lower() or 
    "access denied" in reason.lower() or
    "invalid card" in reason.lower() or
    "unauthorized" in reason.lower()):
```

### Issue #2: Database Schema Error
**Problem:** The access logging was failing due to missing `machine_id` column:
```
(sqlite3.OperationalError) table access_log has no column named machine_id
```

**Fix:** Added graceful fallback handling in `_log_access()` function:
- Try with `machine_id` first (newer schema)
- If column missing, retry without `machine_id` (older schema compatibility)
- Proper transaction rollback on failure

## Files Modified

### 1. app.py - Access Control Callback
**Location:** Lines 271-285
**Change:** Enhanced reason string matching for unregistered cards
**Impact:** Now properly triggers ACCESS_DENIED LED state for unregistered cards

### 2. rfid_control.py - Access Logging
**Location:** `_log_access()` function (lines 599-635)
**Change:** Added database schema compatibility handling
**Impact:** Prevents logging errors from blocking LED state changes

## Expected Behavior After Fix

### Unregistered Card Scan:
1. **Card Detection:** "Card detected, ID: 4132369046"
2. **Access Denial:** "Access denied: Card not found in local database"  
3. **LED Response:** **RED FLASHING** for 3 seconds (ACCESS_DENIED state)
4. **Return to Normal:** Blue/White LOGIN_SCREEN after 3 seconds
5. **Clean Logging:** No database errors

### Other Access Denials:
The fix also handles these scenarios with RED flashing:
- "Card denied" (explicit denial)
- "Access denied" (general denial)
- "Invalid card" (malformed card)
- "Unauthorized" (permission denied)

## Testing Recommendations

### Test Scenario 1: Unregistered Card
1. Present unknown RFID card to reader
2. **Expected:** LED flashes RED for 3 seconds, then returns to blue/white
3. **Log Check:** No database errors, proper "ACCESS_DENIED" log entry

### Test Scenario 2: Registered Card
1. Present known RFID card
2. **Expected:** LED turns GREEN (or PURPLE for admin), user authenticated
3. **Verify:** No regression in normal operation

### Test Scenario 3: Database Schema
1. Check access_log table structure
2. **If missing machine_id:** Logging works without it
3. **If has machine_id:** Logging works with it

## Why This Was Happening

1. **String Mismatch:** RFID controller sent descriptive reason, callback expected specific keyword
2. **Database Error:** Schema mismatch caused silent logging failure
3. **Fallback Logic:** Callback defaulted to LOGIN_SCREEN instead of ACCESS_DENIED
4. **No Visual Feedback:** Users had no indication their card was rejected

The fix ensures unregistered cards now provide clear visual feedback (RED flash) while maintaining robust error handling for database compatibility issues.
