# Chain Reset Instructions

## How to Reset the Chain Controller

To reset `navigation.anchor.rodeDeployed` to 0, send a PUT command with a value of **1** (not 0).

```
PUT /signalk/v1/api/vessels/self/navigation.anchor.rodeDeployed
Value: 1
```

This is counter-intuitive but is how the chain controller interprets the reset command.

## Python Example

```python
import json
import urllib.request

# Send reset command
url = "http://localhost:80/signalk/v1/api/vessels/self/navigation.anchor.rodeDeployed"
data = json.dumps({"value": 1}).encode('utf-8')
req = urllib.request.Request(url, data=data, method='PUT')
req.add_header('Content-Type', 'application/json')
req.add_header('Authorization', f'Bearer {auth_token}')

with urllib.request.urlopen(req, timeout=2) as response:
    print("Reset sent")
```

## Full Reset Sequence

1. **Stop the chain controller**
   ```
   PUT navigation.anchor.command = "stop"
   ```

2. **Reset the rode**
   ```
   PUT navigation.anchor.rodeDeployed = 1   (sends value 1 to trigger reset)
   ```

3. **Wait 1-2 seconds** for chain controller to process

4. **Verify** by reading `navigation.anchor.rodeDeployed` - should be ~0

## Note

The reset routine in `test_autodrop_retrieve.py` already has this implemented correctly at line 103:

```python
# Step 2: Reset rodeDeployed to 0 by sending value of 1
if not send_signalk_command("navigation.anchor.rodeDeployed", 1):
```

