# MCP Servers & Tools Inventory

## Policy & Overview
ResoAI strictly follows least-privilege tool connectivity. All analytical, vector, and ingestion operations are executed via direct local Python modules and deterministic CLI targets defined in the `Makefile`.

## Configured MCP Servers
- **External Servers:** Currently none (`.mcp.json` has `mcpServers: {}`).
- **Policy:** Any future external MCP server must:
  1. Be from an official, verified publisher.
  2. Have its version strictly pinned by hash or exact semantic version (no `@latest` or `:latest`).
  3. Load credentials exclusively via environment variables (never hardcoded in JSON).
  4. Require explicit developer approval for write/destructive capabilities.
  5. Be documented in this inventory with a stated business justification and designated owner.

## Owner
FiftyFive Technologies Core AI Team (`@Ashu199755tech`)
