# TradingView MCP for XAU-ZONES

This project is configured to use your existing TradingView MCP server from:

- `/Users/apple/Documents/xau-auto/tradingview-mcp`

## What was added

- Project MCP config file: `.mcp.json`
- MCP server name: `tradingview`

It runs:

`node /Users/apple/Documents/xau-auto/tradingview-mcp/src/server.js`

## One-time requirements

1. Ensure dependencies are installed in the MCP project:
   - `cd "/Users/apple/Documents/xau-auto/tradingview-mcp" && npm install`
2. Launch TradingView Desktop in debug mode (port `9222`):
   - `/Applications/TradingView.app/Contents/MacOS/TradingView --remote-debugging-port=9222`

## Activate in Cursor

1. Reload/restart Cursor so project MCP config is re-read.
2. Open `xau-zones` project.
3. Verify by asking the agent to run a TradingView health check tool (for example `tv_health_check`).

## Notes

- This links `xau-zones` to your existing MCP install without duplicating files.
- If you move the `xau-auto` folder, update the path in `.mcp.json`.
