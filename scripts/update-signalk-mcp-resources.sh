#!/bin/bash
# Ensures signalk-mcp-server has required resource files
# The MCP server is run via npx, so we check the npm cache
# Usage: ./update-signalk-mcp-resources.sh

set -e

echo "=== SignalK MCP Server Resource Updater ==="
echo ""

# Note: We use npx per the developer's recommendation
# This checks/fixes the globally installed version used by npx -y
echo "Checking signalk-mcp-server installation..."
echo "(Using npx as recommended by developer)"
echo ""

# Find installation directory (global or npx cache)
MCP_DIR=$(npm root -g)/signalk-mcp-server
RESOURCES_DIR="$MCP_DIR/resources"

echo "MCP installation: $MCP_DIR"
echo ""

# Check for resources directory
echo "Checking for resources directory..."
if [ ! -d "$RESOURCES_DIR" ]; then
    echo "⚠️  Resources directory missing - fetching from GitHub..."
    echo ""

    # Clone repo to temp location
    TEMP_DIR=$(mktemp -d)
    echo "Cloning repository to $TEMP_DIR..."
    git clone --depth 1 https://github.com/tonybentley/signalk-mcp-server.git "$TEMP_DIR"

    # Copy resources
    echo "Creating resources directory..."
    mkdir -p "$RESOURCES_DIR"

    echo "Copying resource files..."
    cp -v "$TEMP_DIR/resources"/*.json "$RESOURCES_DIR/"

    # Cleanup
    echo "Cleaning up..."
    rm -rf "$TEMP_DIR"
    echo ""
    echo "✓ Resources restored successfully"
else
    echo "✓ Resources directory already exists"
fi

echo ""
echo "Verifying resource files..."
all_present=true
for file in signalk-overview.json data-model-reference.json path-categories-guide.json mcp-tool-reference.json; do
    if [ -f "$RESOURCES_DIR/$file" ]; then
        size=$(stat -f%z "$RESOURCES_DIR/$file" 2>/dev/null || stat -c%s "$RESOURCES_DIR/$file" 2>/dev/null)
        echo "  ✓ $file ($size bytes)"
    else
        echo "  ✗ $file MISSING"
        all_present=false
    fi
done

echo ""
if [ "$all_present" = true ]; then
    echo "✓ All resource files present"
    echo ""
    echo "MCP server is ready to use!"
    echo ""
    echo "Note: The MCP server runs via npx (as recommended by the developer)"
    echo "Your Claude Code configuration uses: npx -y signalk-mcp-server"
    echo "Restart Claude Code to pick up any changes."
else
    echo "⚠️  Some resource files are missing"
    echo "Please check the GitHub repository or run this script again."
    exit 1
fi
