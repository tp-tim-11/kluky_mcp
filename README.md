# kluky_mcp

MCP server for the Kluky bicycle shop agent.

This repository is intentionally a shell: business logic is left to be implemented later.

## Project layout

- `main.py` composes the server and starts FastMCP.
- `tools/health.py` contains deterministic health-check tooling.
- `tools/uc1.py` contains tool access/show shells (`list_tools`, `find_tool`, `show_tool_position`, `change_tool_status`).
- `tools/uc2.py` contains test-document catalog tools (`get_documents`, `get_document_info`).
- `tools/uc3.py` contains record-management shells (`add_record_if_not_exists`, `get_all_records_for_name`, `update_record`).

## Run locally

```bash
uv run python main.py
```

You can also run it through the FastMCP CLI:

```bash
uv run fastmcp run main.py:mcp
```

## Health check

Use `health_check` to verify end-to-end MCP connectivity. It returns a deterministic,
host-bound SHA-256 proof, which is hard to fake without actually calling the tool.

```bash
uv run fastmcp call main.py health_check challenge="probe-001"
```

Calling the tool repeatedly with the same `challenge` on the same machine should return
the same `proof`.

## Test document catalog

`get_documents` returns a static catalog labeled `TEST_PURPOSE_DOCUMENT_CATALOG`.
This data is intentionally test-only and deterministic for integration checks.

## OpenCode local MCP config

Add this to your project `opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "kluky": {
      "type": "local",
      "command": ["uv", "run", "python", "main.py"],
      "enabled": true
    }
  }
}
```
