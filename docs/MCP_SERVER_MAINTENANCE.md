# SignalK MCP Server Maintenance Guide

## Overview

The SignalK MCP server provides AI agents (like Claude Code) with streamlined access to vessel data. This guide documents the setup, the npm packaging bug, and how to maintain it.

## The NPM Packaging Bug

**Issue**: The `signalk-mcp-server` npm package (v1.0.8) is missing the `resources/` directory that contains documentation files needed by the `get_initial_context()` tool.

**Missing Files**:
- `signalk-overview.json` - SignalK core concepts
- `data-model-reference.json` - Path reference documentation
- `path-categories-guide.json` - Path categorization guide
- `mcp-tool-reference.json` - MCP tool usage patterns

**Impact**:
- MCP server shows warnings about missing resources on startup
- The `get_initial_context()` tool returns incomplete documentation
- Does NOT prevent the MCP server from functioning

## Current Fix Applied

The missing resource files have been manually copied to:
```
/home/doug/.nvm/versions/node/v20.19.5/lib/node_modules/signalk-mcp-server/resources/
```

## Maintenance Script

Use this script to restore resources. The MCP server is run via **npx** (as recommended by the developer), but the script ensures the globally cached version has the required files:

```bash
#!/bin/bash
# File: update-signalk-mcp-resources.sh
# Ensures signalk-mcp-server has required resource files

set -e

echo "Checking signalk-mcp-server installation..."
# Note: We use npx per developer recommendation
# This checks the globally installed version used by npx -y

MCP_DIR=$(npm root -g)/signalk-mcp-server
RESOURCES_DIR="$MCP_DIR/resources"

echo "Checking for resources directory..."
if [ ! -d "$RESOURCES_DIR" ]; then
    echo "Resources directory missing - fetching from GitHub..."

    # Clone repo to temp location
    TEMP_DIR=$(mktemp -d)
    git clone --depth 1 https://github.com/tonybentley/signalk-mcp-server.git "$TEMP_DIR"

    # Copy resources
    mkdir -p "$RESOURCES_DIR"
    cp "$TEMP_DIR/resources"/*.json "$RESOURCES_DIR/"

    # Cleanup
    rm -rf "$TEMP_DIR"

    echo "✓ Resources restored"
else
    echo "✓ Resources directory exists"
fi

# Verify files
echo "Verifying resource files..."
for file in signalk-overview.json data-model-reference.json path-categories-guide.json mcp-tool-reference.json; do
    if [ -f "$RESOURCES_DIR/$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file MISSING"
    fi
done

echo "Done!"
```

## MCP Server Configuration

Location: `~/.claude/settings.json`

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

## How MCP Integration Works

1. **Claude Code starts MCP servers** - When Claude Code starts, it reads `~/.claude/settings.json` and launches configured MCP servers as child processes
2. **Communication via stdio** - MCP servers communicate with Claude Code using stdin/stdout
3. **Tools are loaded dynamically** - MCP tools don't appear in Claude's static tool list but are available when needed
4. **npx usage (recommended)** - Using `npx -y signalk-mcp-server` runs the package on-demand without requiring global installation. This is the **developer's recommended approach**. The `-y` flag automatically confirms package execution.

## Verifying MCP Server Works

### Method 1: Check Claude Code startup logs
Look for MCP server connection messages when Claude Code starts.

### Method 2: Test with code execution
Ask Claude Code to query vessel data using the MCP:
```
"Use the SignalK MCP execute_code tool to get the current vessel position"
```

### Method 3: Manual test
```bash
# Start MCP server manually
SIGNALK_HOST=localhost SIGNALK_PORT=80 npx signalk-mcp-server

# Should show:
# [CODE MODE] Code execution enabled
# signalk-mcp-server v1.0.0 running on stdio
# SignalK HTTP connection verified
# SignalK client connected successfully
```

## MCP Server Capabilities

The SignalK MCP server provides an `execute_code` tool that runs JavaScript in a V8 isolate with these async functions:

- `getVesselState()` - Full vessel data
- `getAisTargets({ page, pageSize, maxDistance })` - AIS targets
- `getActiveAlarms()` - System alarms
- `listAvailablePaths()` - Available SignalK paths
- `getPathValue(path)` - Specific path values
- `getConnectionStatus()` - Connection health

## When to Update

Run the maintenance script when:
- The MCP server shows resource file warnings on startup
- After clearing npm cache (`npm cache clean`)
- After reinstalling Node.js/npm
- When switching Node.js versions (nvm)

**Note**: Since we use `npx -y` per the developer's recommendation, npm automatically manages the package version. The script only needs to restore the missing resource files if they disappear.

## Future Considerations

This workaround will be unnecessary when:
- The npm package is fixed to include resources
- The MCP server is updated to handle missing resources gracefully
- An alternative MCP server implementation is used

## Related Files

- Configuration: `~/.claude/settings.json`
- MCP package: `~/.nvm/versions/node/v20.19.5/lib/node_modules/signalk-mcp-server/`
- Resources: `~/.nvm/versions/node/v20.19.5/lib/node_modules/signalk-mcp-server/resources/`

## References

- [GitHub Repository](https://github.com/tonybentley/signalk-mcp-server)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [Claude Code MCP Documentation](https://docs.anthropic.com/claude/docs/model-context-protocol)
