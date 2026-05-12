# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (dev)
uv sync --extra dev

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_list_tools.py

# Run a specific test
uv run pytest tests/test_list_tools.py::test_list_tools

# Run the MCP server locally
uv run mitmproxy-mcp

# Lint (ruff is configured in pyproject.toml, install separately if needed)
uv run ruff check src/
```

## Architecture

This is an **MCP (Model Context Protocol) server** that wraps mitmproxy, allowing LLMs to control an HTTP/HTTPS proxy and analyze captured traffic.

### Entry point and MCP tool registration

All MCP tools are defined as `@mcp.tool()` decorated async functions in `src/mitmproxy_mcp/core/server.py`. This single file is the hub — it instantiates `MitmController` (a singleton), wires up all tools, and exposes them via `FastMCP`. `start()` at the bottom of `server.py` is the CLI entrypoint declared in `pyproject.toml`.

### Core components

- **`MitmController`** (`server.py`) — owns the mitmproxy `DumpMaster`, `ScopeManager`, `TrafficRecorder`, `TrafficInterceptor`, and session variables dict. All MCP tools call into this object.
- **`TrafficRecorder`** (`core/recorder.py`) — mitmproxy addon that saves flows to a SQLite DB (`mitm_mcp_traffic.db`). Provides search, detail lookup, bulk-export for analysis, and `.mitm` file import. Headers are stored as ordered `[[key, value]]` lists in JSON.
- **`TrafficInterceptor`** (`core/interceptor.py`) — mitmproxy addon that applies `InterceptionRule` objects to modify in-flight traffic (inject headers, regex-replace body, block requests).
- **`ScopeManager`** (`core/scope.py`) — filters flows by allowed domains and ignored extensions/methods before they reach the recorder.
- **`generation.py`** (`core/generation.py`) — Jinja2-based code generator. Renders scraper code from captured flows using templates in `src/mitmproxy_mcp/templates/` (curl_cffi, requests, aiohttp, playwright).

### Data models

`models.py` defines Pydantic v2 models: `InterceptionRule`, `ScopeConfig`, `RequestData`, and others used as structured return types.

### Key design detail

Traffic replay uses `curl-cffi`'s `AsyncSession` (not `httpx`) to impersonate browser TLS fingerprints. The mitmproxy CA cert (`~/.mitmproxy/mitmproxy-ca-cert.pem`) is auto-detected and used for SSL verification during replay if present.

### Tests

Tests live in both `tests/` (top-level) and `src/mitmproxy_mcp/tests/`. Run with `pytest` — uses `pytest-asyncio` for async test functions.
