# SignalK Anchor Alarm Connector

## Project Overview

This is a SignalK plugin that creates an automation bridge between an anchor windlass chain counter and the [signalk-anchoralarm-plugin](https://github.com/sbender9/signalk-anchoralarm-plugin). It automatically manages anchor alarm activation/deactivation based on chain deployment activity.

**Purpose**: Eliminate manual anchor alarm management by automatically setting/unsetting the alarm when the windlass deploys or retrieves anchor rode.

**Repository**: https://github.com/dougkimmerly/signalk-anchorAlarmConnector

## Directory Structure

```
signalk-anchorAlarmConnector/
├── CLAUDE.md              # This file - project overview
├── README.md              # GitHub readme
├── package.json
│
├── plugin/                # SignalK plugin code
│   ├── index.js           # Main plugin entry point
│   ├── testingSimulator.js # Physics simulation orchestrator
│   ├── tokenManager.js    # Authentication management
│   ├── config/
│   │   └── simulationConfig.js  # Simulation parameters
│   ├── physics/           # Physics engine modules
│   │   ├── boat.js, environment.js, integrator.js
│   │   └── forces/        # Force calculations (wind, drag, motor, constraint)
│   └── data/              # Runtime data (config.json, token.json)
│
├── validation/            # Validation framework
│   ├── CLAUDE.md          # Validation framework documentation (see below)
│   ├── scripts/           # Main validation scripts
│   ├── data/              # Test results and temporary data
│   ├── unit/              # JavaScript unit tests
│   ├── analysis/          # Analysis tools and reports
│   ├── utils/             # Shared Python utilities
│   └── docs/              # Validation documentation
│
├── scripts/               # Maintenance scripts
│   └── update-signalk-mcp-resources.sh  # MCP server resource updater
│
└── docs/                  # Architecture documentation
    ├── SIGNALK_GUIDE.md           # Quick reference for SignalK concepts and paths
    ├── MCP_SERVER_MAINTENANCE.md  # SignalK MCP server maintenance guide
    ├── SIMULATION_ARCHITECTURE.md
    ├── SIMULATION_DOCUMENTATION.md
    └── SYSTEM_ARCHITECTURE.md
```

## Validation Framework

For detailed validation framework documentation, see **[validation/CLAUDE.md](validation/CLAUDE.md)**.

### Specialized Agents for Validation

To manage context efficiently, use specialized agents for validation tasks:
- **Python Coder Agent** - Python code changes in validation framework
- **Test Analyzer Agent** - Test result analysis and issue identification

See [validation/AGENT_GUIDE.md](validation/AGENT_GUIDE.md) for usage guide.

Quick commands:
```bash
# Run physics unit tests
node test/unit/physics.test.js

# Run overnight test suite
cd test/scripts && python3 overnight_test_runner.py

# Quick 4-corner validation
cd test/scripts && python3 quick_validation_test.py
```

## ⚠️ CRITICAL SIMULATION CONCEPTS

**ALWAYS REMEMBER**: During anchor deployment, the chain controller waits for the boat to move farther away before deploying more chain.

### Chain Deployment Physics
- **Deployment**: Boat moves AWAY from anchor → chain follows → motor BACKWARD helps boat move away
- **Negative slack during deployment** = Boat is TOO FAR away (chain fully extended)
  - Motor BACKWARD would make it worse
  - Motor must STOP and wait for boat to drift closer naturally
- **Retrieval**: Boat moves TOWARD anchor → chain follows → motor FORWARD helps boat move closer

See [docs/SIMULATION_DOCUMENTATION.md](docs/SIMULATION_DOCUMENTATION.md) for complete physics details.

## How It Works

### Automatic Anchor Drop Detection
When the deployed rode length (`navigation.anchor.rodeDeployed`) exceeds the sum of water depth (`environment.depth.belowSurface`) and bow height (`design.bowAnchorHeight`), the plugin:
1. Sends `dropAnchor` command to the anchor alarm plugin
2. Records the anchor depth
3. Begins monitoring for anchor settling

### Automatic Anchor Raise Detection
When the deployed rode becomes less than depth + bow height while the anchor is set, the plugin:
1. Sends `raiseAnchor` command to the anchor alarm plugin
2. Resets the anchor state
3. Updates scope to 0

### Manual Anchor Setting (via Skipper App)
The anchor alarm is set manually using the SKipper app button, which triggers a PUT to `navigation.anchor.setAnchor`. This:
1. Reads current anchor depth from position altitude
2. Sends `setManualAnchor` command with anchor depth and rode length
3. Sends `setRodeLength` command to update alarm radius

Note: Automatic 120-second settling was disabled - use the SKipper app button instead.

## Key Data Paths

### Input Paths (Monitored)
- `navigation.anchor.rodeDeployed` - Current amount of chain deployed (meters)
- `navigation.anchor.rodeLength` - Total available chain length (meters)
- `navigation.anchor.position` - Anchor GPS position (latitude/longitude/altitude)
- `navigation.anchor.distanceFromBow` - Distance from bow to anchor (meters)
- `navigation.anchor.command` - Commands from external systems
- `environment.depth.belowSurface` - Water depth (meters)
- `design.bowAnchorHeight` - Bow anchor height above waterline (meters, default: 2)
- `navigation.position` - Vessel GPS position
- `navigation.headingTrue` - Vessel heading in radians

### Output Paths (Published)
- `navigation.anchor.autoReady` - Boolean indicating if all systems are operational
- `navigation.anchor.scope` - Calculated anchor scope (rode length / total depth)

## Anchor Alarm Plugin Integration

This plugin communicates with the [signalk-anchoralarm-plugin](https://github.com/sbender9/signalk-anchoralarm-plugin) via REST API.

### Available Commands

**Anchor Alarm Plugin Commands (POST requests):**
These are action commands to the anchor alarm plugin at `http://[server]:[port]/plugins/anchoralarm/[command]`

- `POST /plugins/anchoralarm/dropAnchor` - Marks anchor as dropped at current position
- `POST /plugins/anchoralarm/raiseAnchor` - Marks anchor as raised, disables alarm
- `POST /plugins/anchoralarm/setRodeLength` - Sets alarm radius based on rode length
  - Body: `{"length": <meters>}`
- `POST /plugins/anchoralarm/setManualAnchor` - Manually sets anchor position with depth
  - Body: `{"anchorDepth": <meters>, "rodeLength": <meters>}`
- `POST /plugins/anchoralarm/setRadius` - Calculates radius from current position

**SignalK Standard PUT Handlers:**
These use SignalK's standard PUT API for setting values:

- `PUT navigation.anchor.setAnchor` - Sets the anchor alarm (called from SKipper app button)

### Anchor Alarm Plugin Features
- Default alarm radius: 5× water depth when depth sensor available
- Web interface: `http://[server]:[port]/signalk-anchoralarm-plugin/`
- Map overlays: `/?openseamap` (maritime charts), `/?satellite` (satellite imagery)
- Requires authentication via SignalK UI

## Architecture

### Core Files

**[plugin/index.js](plugin/index.js)** - Main plugin logic
- Token-based authentication with SignalK server
- Subscription management for anchor-related data paths
- Automatic anchor drop/raise detection
- Anchor settling detection and automatic setup
- Communication with anchor alarm plugin via HTTP API

**[plugin/tokenManager.js](plugin/tokenManager.js)** - Authentication handler
- Manages OAuth token acquisition and storage
- Handles token refresh and persistence

**[plugin/testSimulation.js](plugin/testSimulation.js)** - Development testing simulation
- Wind-based physics simulation for realistic anchor behavior
- Simulates boat drift, wind gusts, and anchor rode tension
- Updates position, heading, depth, and wind data
- FOR TESTING ONLY - Should be disabled in production

### Configuration

Plugin settings (configured in SignalK server UI):
- `serverBaseUrl` - SignalK server URL (default: `http://localhost:80`)
- `clientId` - Unique client identifier (default: `signalk-anchor-alarm-connector`)
- `description` - Client description for access requests
- `testMode` - Enable/disable test simulation (default: `false`)

### State Management

Key state variables in [plugin/index.js](plugin/index.js):
- `rodeDeployed` - Current deployed rode length
- `anchorDropped` - Boolean indicating if anchor position exists
- `anchorSet` - Boolean indicating if anchor has settled
- `depth` - Current water depth
- `rodeLength` - Total available rode length
- `bowHeight` - Bow height above waterline
- `anchorDepth` - Depth at which anchor was set
- `lastChainMove` - Timestamp of last chain movement
- `lastPosition`, `lastDepth`, `lastCounterConnection` - Health check timestamps

### Timing Behavior

- **Startup delay**: 3 seconds to allow SignalK paths to establish
- **Subscription periods**:
  - Active mode (anchor moving): 1000ms updates
  - Settled mode (anchor set): 20000ms updates
- **Settling timeout**: 120 seconds (2 minutes) of no chain movement
- **Auto-ready checks**:
  - Position updated within 30 seconds
  - Depth updated within 30 seconds
  - Counter connection within 60 seconds
- **Drop command debounce**: 5 seconds between drop commands

## Test Simulation

The test simulation provides realistic anchor behavior for development and testing.

### Enabling/Disabling Test Mode

Test mode can be controlled via the plugin configuration in the SignalK server UI:

1. Navigate to Server → Plugin Config → Anchor Alarm Connector
2. Toggle the "Enable Test Simulation" checkbox
3. Restart the plugin for changes to take effect

When enabled (`testMode: true`):
- Wind-based physics simulation runs automatically
- Simulated position, depth, wind, and heading data
- Console logs indicate "Test mode enabled - starting wind-based anchor simulation"

When disabled (`testMode: false`, default):
- No simulation runs
- Plugin operates with real vessel data
- Console logs indicate "Test mode disabled - running in production mode"

### Physics Model
- **Wind force**: Proportional to wind speed² (knots to m/s conversion)
- **Rode tension**: Spring-like restoring force toward anchor
- **Water drag**: Velocity damping
- **Boat mass**: 5000kg (configurable in testSimulation.js)
- **Time step**: 0.5 seconds

### Wind Simulation
- Initial: 10 knots from 180° (south)
- Gusts: ±3 knots random variation
- Shifts: ±2° every 10 seconds
- Range: 5-20 knots
- Updates every 10 seconds

### Boat Behavior
- Heading automatically points into wind (wind direction + 180°)
- Drifts downwind when rode deployed
- Settles within catenary-calculated swing radius
- Responds realistically to wind changes

### Test Coordinates
- Initial position: 43.59738°N, -79.5073°W
- Initial depth: 5 meters
- Bow height: 2 meters

## Data Flow

### Anchor Drop Sequence
1. User pays out rode via windlass
2. `navigation.anchor.rodeDeployed` increases
3. When rode > (depth + bowHeight):
   - Plugin sends `dropAnchor` command
   - Records `lastChainMove` timestamp
   - Sets `anchorDepth` = current depth
   - Resets `anchorSet` to false

### Anchor Settling Sequence
1. Rode stops moving for 120 seconds
2. Plugin calculates anchor depth from position altitude
3. Sends `setManualAnchor` with anchor depth and rode length
4. Sends `setRodeLength` to update alarm radius
5. Calculates scope: `rodeDeployed / (anchorDepth + bowHeight)`
6. Publishes scope to `navigation.anchor.scope`
7. Sets `anchorSet` to true
8. Changes update period to 20 seconds (less frequent)

### Anchor Raise Sequence
1. User retrieves rode via windlass
2. `navigation.anchor.rodeDeployed` decreases
3. When rode < (depth + bowHeight):
   - Plugin sends `raiseAnchor` command
   - Resets `anchorSet` to false
   - Sets scope to 0

## Dependencies

- **axios** (^1.12.2) - HTTP client for anchor alarm API calls
- SignalK server with plugin support
- [signalk-anchoralarm-plugin](https://github.com/sbender9/signalk-anchoralarm-plugin) installed and running

## Development Notes

### Authentication
- Uses token-based authentication via tokenManager
- Tokens stored in plugin data directory
- Automatic token refresh handling

### Subscription Management
- Uses `app.subscriptionmanager.subscribe()` for data path monitoring
- Unsubscribes tracked in `unsubscribes` array
- Delta updates processed in subscription callback

### Error Handling
- Failed token acquisition prevents plugin startup
- HTTP errors logged with response details
- Invalid numbers filtered using `isValidNumber()` helper

### Debugging
- Use `app.debug()` for development logging
- Console logs show command sending and responses
- Test simulation provides periodic status updates

## Health Monitoring

The plugin sets `navigation.anchor.autoReady` based on:
- Position data freshness (< 30 seconds old)
- Depth data freshness (< 30 seconds old)
- Counter connection health (< 60 seconds old)

This indicates whether the automation system is fully operational.

## Future Enhancements

Potential improvements:
- Configurable settling timeout (currently hardcoded to 120s)
- Configurable update periods for active/settled modes
- Alert notifications for anchor dragging
- Integration with boat heading for rode angle calculation
- Multi-anchor support
- Rode angle/catenary calculations
- Wind compensation for alarm radius

## Troubleshooting

**Anchor doesn't auto-drop:**
- Verify `navigation.anchor.rodeDeployed` is updating
- Check rode > (depth + bow height)
- Ensure anchor alarm plugin is running
- Check 5-second debounce hasn't blocked command

**Anchor doesn't auto-raise:**
- Verify rode < (depth + bow height)
- Check anchor position exists before raise
- Verify anchor alarm plugin connectivity

**Scope shows 0:**
- Wait 2 minutes after chain stops moving
- Check anchor position has altitude data
- Verify depth + bowHeight is not zero
- Check for NaN/Infinity in calculation

**autoReady shows false:**
- Check position updates are current
- Verify depth sensor is working
- Ensure anchor alarm plugin is responding

## SignalK Authentication

### Web Interface Login

The SignalK server requires authentication for web interfaces, including the anchor alarm plugin web UI.

**Default Admin Credentials:**
- URL: `http://localhost:80/admin/#/login`
- Username: `admin`
- Password: Set during initial setup (example: `signalk`)

**Security Configuration:**
- Located at: `~/.signalk/security.json`
- Contains user accounts, permissions, and device access settings
- Settings:
  - `allow_readonly`: true (allows read-only API access without auth)
  - `allowNewUserRegistration`: true
  - `allowDeviceAccessRequests`: true

### API Authentication

**Login via REST API:**
```bash
curl -X POST http://localhost:80/signalk/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"signalk"}'
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Authentication Cookies Set:**
1. `JAUTHENTICATION` - JWT token for API authentication
2. `skLoginInfo` - Login status indicator

**Using the Token:**
```bash
# In Authorization header
curl -H "Authorization: Bearer <token>" http://localhost:80/signalk/v1/api/...

# Or via cookie (automatically set by browser after login)
```

### Web Interface Access

**Anchor Alarm Plugin:**
- URL: `http://localhost:80/signalk-anchoralarm-plugin/`
- Requires login
- Displays interactive map with boat position and heading
- Shows boat icon oriented according to `navigation.headingTrue`
- Updates position and heading every 1.5 seconds

**SignalK Admin UI:**
- URL: `http://localhost:80/admin/`
- Plugin configuration: Server → Plugin Config
- Security settings: Security → Users

### Read-Only API Access

The REST API allows read-only access without authentication:
```bash
# These work without login
curl http://localhost:80/signalk/v1/api/vessels/self
curl http://localhost:80/signalk/v1/api/vessels/self/navigation/headingTrue
```

## SignalK MCP Server Integration

This project includes integration with the [SignalK MCP Server](https://github.com/tonybentley/signalk-mcp-server), which provides AI agents (like Claude Code) with streamlined access to vessel data through the Model Context Protocol.

### Configuration

The MCP server is configured in `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "signalk": {
      "command": "npx",
      "args": ["-y", "signalk-mcp-server"],
      "env": {
        "SIGNALK_HOST": "localhost",
        "SIGNALK_PORT": "80"
      }
    }
  }
}
```

### MCP Server Capabilities

The MCP provides an `execute_code` tool that runs JavaScript with these async functions:
- `getVesselState()` - Full vessel data (position, heading, speed, etc.)
- `getAisTargets({ page, pageSize, maxDistance })` - AIS target data
- `getActiveAlarms()` - System alarms and notifications
- `listAvailablePaths()` - Available SignalK paths
- `getPathValue(path)` - Specific path values
- `getConnectionStatus()` - Connection health status

### Maintenance

**Important**: The npm package has a bug where resource files are missing. The configuration uses `npx` (per developer recommendation), which automatically manages the package. If resource file warnings appear, run:

```bash
./scripts/update-signalk-mcp-resources.sh
```

See [docs/MCP_SERVER_MAINTENANCE.md](docs/MCP_SERVER_MAINTENANCE.md) for details.

### Benefits

- **Token efficiency**: 90-96% reduction in token usage vs direct API calls
- **Simplified queries**: Filter and process data before returning to AI
- **Type-safe**: V8 isolate execution with SignalK SDK
- **Real-time**: Direct connection to SignalK server

## Deployment

### Server Details

- **URL**: `http://192.168.20.166:3000`
- **SSH**: `doug@192.168.20.166`
- **Plugin Path**: `/home/doug/src/signalk-anchorAlarmConnector`
- **Symlink**: `~/.signalk/node_modules/signalk-anchoralarmconnector` → `../../src/signalk-anchorAlarmConnector`
- **Auth**: JWT Bearer tokens (admin/signalk)
- **Plugin ID**: `signalk-anchoralarmconnector`

### Deploy Changes to Production

```bash
# 1. SSH to server
ssh doug@192.168.20.166

# 2. Navigate to plugin directory
cd /home/doug/src/signalk-anchorAlarmConnector

# 3. Check for local changes
git status

# 4. Stash local changes if needed
git stash

# 5. Pull latest changes
git pull

# 6. Restore local changes if needed
git stash pop

# 7. DO NOT restart SignalK manually
# PM (orchestrator) manages service restarts
```

### Verify Deployment

```bash
# Check plugin is running
sudo journalctl -u signalk --since "1 minute ago" | grep -i anchor

# View SignalK logs
sudo journalctl -u signalk -f
```

## Links & Resources

- [Anchor Alarm Plugin Repository](https://github.com/sbender9/signalk-anchoralarm-plugin)
- [SignalK MCP Server](https://github.com/tonybentley/signalk-mcp-server)
- [SignalK Server Documentation](https://demo.signalk.org/documentation/)
- [SignalK Plugin API](https://demo.signalk.org/documentation/develop/plugins/server_plugin.html)
- [SignalK Security Documentation](https://demo.signalk.org/documentation/security.html)
- [Model Context Protocol](https://modelcontextprotocol.io/)