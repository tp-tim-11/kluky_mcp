# kluky_mcp

Blueprint-aligned MCP server skeleton for the Kluky team.

The repository is intentionally a scaffold. Tool contracts, naming, and packaging are production-shaped, while business logic is intentionally unimplemented for the team to fill in.

## Project layout

```text
kluky_mcp/
├── opencode.json
├── pyproject.toml
├── src/
│   └── kluky_mcp/
│       ├── __init__.py
│       ├── api_client.py
│       ├── constants.py
│       ├── formatters.py
│       ├── models.py
│       ├── server.py
│       └── tools/
│           ├── __init__.py
│           ├── health.py
│           ├── uc1.py
│           ├── uc2.py
│           └── uc3.py
├── tests/
│   ├── test_health.py
│   ├── test_server.py
│   ├── test_uc1_tools.py
│   ├── test_uc2_documents.py
│   └── test_uc3_records.py
└── evaluation.xml
```

## Run locally

```bash
uv run --python 3.13 python -m kluky_mcp.server
```

## Import choice: FastMCP-native

This project intentionally uses `fastmcp` imports directly (`from fastmcp import FastMCP`) instead of importing through `mcp.server.fastmcp`.

Why this choice:

- It matches the team direction to build and maintain the server as a FastMCP-first project.
- It keeps application code aligned with the standalone FastMCP docs and CLI workflows.
- It avoids direct dependency on `mcp.types` in app code by passing tool annotations as dictionaries, which FastMCP supports natively.

Note: FastMCP still depends on the underlying `mcp` protocol package transitively, but this repository does not import `mcp` directly in server/tool modules.

## CLI smoke test

```bash
uv run fastmcp list --command "uv run --python 3.13 python -m kluky_mcp.server"
uv run fastmcp call --command "uv run --python 3.13 python -m kluky_mcp.server" --target kluky_health_check --input-json '{"params":{"challenge":"probe-001"}}'
```

## OpenCode config

`opencode.json` is already configured to launch the server as a local MCP process:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "kluky": {
      "type": "local",
      "command": ["uv", "run", "--python", "3.13", "python", "-m", "kluky_mcp.server"],
      "enabled": true
    }
  }
}
```

## Tool groups

- `uc1`: `kluky_list_tools`, `kluky_find_tool`, `kluky_show_tool_position`, `kluky_change_tool_status`
- `uc2`: `kluky_get_documents`, `kluky_get_document_info`
- `uc3`: `kluky_add_record_if_not_exists`, `kluky_get_all_records_for_name`, `kluky_update_record`
- `health`: `kluky_health_check`

## Placeholder behavior

All tools currently return placeholders only. This includes `kluky_health_check`.

Examples:

- `kluky_find_tool`, `kluky_show_tool_position`, `kluky_change_tool_status`,
  `kluky_add_record_if_not_exists`, and `kluky_update_record` return a
  `NOT_IMPLEMENTED: ...` string.
- `kluky_get_documents` and `kluky_health_check` return a placeholder JSON object.
- `kluky_list_tools` and `kluky_get_all_records_for_name` return empty lists.

`api_client.py` is also a stub and intentionally raises/returns
`NOT_IMPLEMENTED` placeholders until real integration is added.

## Test and evaluation skeletons

- `tests/` contains skipped test skeletons to implement.
- `evaluation.xml` contains a 10-question evaluation scaffold for future LLM evaluation runs.
