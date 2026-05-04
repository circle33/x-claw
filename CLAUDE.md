# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

x-claw is a Python async HTTP client using httpx. Currently a single-file project (`main.py`) that fetches web pages asynchronously.

## Development Setup

- **Python**: 3.12+ (managed via uv)
- **Package manager**: [uv](https://docs.astral.sh/uv/) — uses `uv.lock` for dependency locking
- **Install dependencies**: `uv sync`
- **Run**: `uv run python main.py`

## Key Dependency

- `httpx` — async HTTP client (used with `AsyncClient`)
