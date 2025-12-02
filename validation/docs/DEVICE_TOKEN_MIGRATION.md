# Device Token Authentication Migration

## Overview

Test scripts have been updated to use the same device token authentication method as the plugin, instead of temporary user login tokens. This provides better reliability and eliminates the need for hardcoded credentials.

## What Changed

### Before (User Login Method)
```python
# Old approach - temporary tokens that expire
token = get_auth_token()  # Calls /signalk/v1/auth/login
```

### After (Device Token Method)
```python
# New approach - persistent device token
token = get_device_token()  # Reads from plugin/data/token.json
# Falls back to user login if device token unavailable
token = get_auth_token()
```

## Files Modified

### Core Changes
- **[test/utils/common.py](../utils/common.py)** - Added `get_device_token()` function, updated `get_auth_token()`
- **[test/scripts/reset_anchor.py](../scripts/reset_anchor.py)** - Now uses shared authentication from common.py
- **[test/scripts/stop_chain.py](../scripts/stop_chain.py)** - Now uses shared authentication from common.py

### New Files
- **[test/scripts/verify_device_token.py](../scripts/verify_device_token.py)** - Helper to check device token availability

## Setup Instructions

### Step 1: Approve the Plugin in SignalK Admin (One-Time)

The plugin needs approval only once:

1. **Open SignalK Admin UI**: `http://localhost:80/admin/`
2. **Login** with your SignalK credentials (default: admin/signalk)
3. **Navigate to**: Security → Access Requests
4. **Find**: "signalk-anchor-alarm-connector" request
5. **Click**: "APPROVE" button

The device token is automatically saved to `plugin/data/token.json`

### Step 2: Verify Token is Available

Run the verification script before running tests:

```bash
cd test/scripts
python3 verify_device_token.py
```

Expected output:
```
Checking for device token...

✓ Device token is available
✓ Token length: 256 characters

All test scripts can now use this device token for authentication.
```

### Step 3: Run Tests

Test scripts now automatically use the device token:

```bash
# Reset anchor
python3 reset_anchor.py

# Stop chain
python3 stop_chain.py

# Run main test suite
python3 overnight_test_runner.py
```

## Benefits

1. **No Expiration Issues** - Device tokens can be permanent
2. **Single Approval** - One-time approval in SignalK admin
3. **No Hardcoded Credentials** - No username/password in test scripts
4. **Consistent Authentication** - Plugin and tests use identical method
5. **Backwards Compatible** - Falls back to user login if needed

## Troubleshooting

### Error: "No device token found"

**Cause**: Plugin hasn't been approved in SignalK admin yet

**Fix**:
1. Go to SignalK admin: `http://localhost:80/admin/`
2. Navigate to Security → Access Requests
3. Approve the "signalk-anchor-alarm-connector" request
4. Wait 1-2 seconds for token to be written
5. Try again

### Error: "Device token expired"

**Cause**: Device token has expired (rare with permanent tokens)

**Fix**:
1. Delete the old token file: `plugin/data/token.json`
2. Go to SignalK admin and approve the request again
3. Try again

### Tests still failing after approval

**Cause**: Token file may not be readable or in wrong location

**Verify**:
```bash
# Check token file exists
ls -la plugin/data/token.json

# Check token contents (should contain valid JSON)
cat plugin/data/token.json
```

## How It Works

### Token Loading Flow

```
Test Script calls get_auth_token()
    ↓
Tries get_device_token() first
    ↓
Reads plugin/data/token.json
    ↓
Checks token validity (not expired)
    ↓
Returns device token ✓
    ↓
If device token unavailable:
    ↓
Falls back to user login (/auth/login)
    ↓
Returns session token
```

### Device Token Format

The device token file (`plugin/data/token.json`) contains:

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expiration": null
}
```

- `token`: JWT bearer token for authentication
- `expiration`: null (permanent) or timestamp in milliseconds

## Migration Notes

### For Existing Test Scripts

Scripts outside of `test/scripts/` and `test/utils/` may still have their own `get_auth_token()` function. They will work but can be simplified by using the shared function:

```python
# Add to top of script
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
from common import get_auth_token

# Remove local get_auth_token() function
# Now calls shared version from common.py
```

### Backwards Compatibility

The implementation maintains backwards compatibility:
- Tries device token first (preferred)
- Falls back to user login if device token unavailable
- Works with both permanent and expiring tokens

## Related Documentation

- [FRAMEWORK_OVERVIEW.md](FRAMEWORK_OVERVIEW.md) - Overall test framework structure
- [test/CLAUDE.md](../CLAUDE.md) - Test documentation entry point
- [docs/SIGNALK_GUIDE.md](../../docs/SIGNALK_GUIDE.md) - SignalK concepts and authentication

## Questions?

Refer to the test framework documentation or check the device token migration plan in the project root.
