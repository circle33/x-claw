# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

x-claw is a FastAPI REST API that proxies Twitter/X (via twscrape) and Reddit (via httpx + `.json` endpoints) data. Authentication is cookie-based: browser-exported cookie files are loaded from the `cookies/` directory at startup.

## Development Commands

```bash
uv sync                                        # install dependencies
uv run uvicorn app.main:app --reload           # run dev server (http://localhost:8000/docs)
```

No test or lint configuration is set up in the project.

### Environment Variables (`.env`)

| Variable | Default | Notes |
|---|---|---|
| `COOKIES_DIR` | `./cookies` | cookie file root |
| `DB_PATH` | `./accounts.db` | twscrape account DB |
| `PROXY` | system `https_proxy`/`HTTPS_PROXY` | optional proxy |

## Architecture

FastAPI lifespan initializes two stateful clients at startup, stored on `app.state` and injected with `Depends()`:

- `app.state.twscrape_api` → `Depends(get_api)` in Twitter endpoints
- `app.state.reddit_client` → `Depends(get_reddit_client)` in Reddit endpoints

```
app/
├── main.py                  # lifespan: loads cookies, creates API clients
├── core/
│   ├── config.py            # pydantic-settings (reads .env)
│   ├── twscrape.py          # twscrape API instance + account loader
│   └── reddit.py            # RedditClient (httpx.AsyncClient wrapper)
├── api/v1/
│   ├── router.py            # aggregates all routers under /api/v1
│   └── endpoints/           # tweets, users, trends, reddit_posts, reddit_users, reddit_subreddit
└── schemas/                 # Pydantic response models
```

### Twitter/X Cookie Loading

Cookie files live at `cookies/x/@<username>.json` (browser-exported JSON array).  
`load_accounts()` extracts `auth_token` + `ct0` from each file, calls `api.pool.add_account()`, then `login_all()`.  
Manage accounts via the twscrape CLI — not through this API.

### Reddit Client

Cookie files live at `cookies/reddit/<username>.json`; all are merged into one httpx session.  
Uses Reddit's unauthenticated `.json` suffix endpoints (e.g. `/r/python.json`). No OAuth required.  
User-Agent is randomized via `fake-useragent`.

### Data Parsing

- Twitter endpoints return twscrape object `.dict()` directly.
- Reddit endpoints parse raw JSON manually with `_parse_post()` / `_parse_comment()` inside each endpoint file; comments are parsed recursively.

### API Endpoints (prefix `/api/v1`)

| Router | Endpoints |
|---|---|
| tweets | `GET /tweets/search`, `/tweets/{id}`, `/tweets/{id}/replies`, `/tweets/{id}/retweeters` |
| users | `GET /users/username/{username}`, `/users/{id}`, `/users/{id}/tweets`, `/users/{id}/followers`, `/users/{id}/following` |
| trends | `GET /trends/{category}` |
| reddit-posts | `GET /reddit/posts/search`, `/reddit/posts/{subreddit}/{post_id}`, `/reddit/posts/{subreddit}/{post_id}/comments` |
| reddit-users | `GET /reddit/users/{username}`, `/reddit/users/{username}/posts`, `/reddit/users/{username}/comments` |
| reddit-subreddit | `GET /reddit/subreddit/{name}`, `/reddit/subreddit/popular` |

## MCP Integration

`mcp/` contains a separate `mitmproxy-mcp` server project with its own `pyproject.toml`, tests, and Docker setup. It is wired up in `.mcp.json` as a stdio MCP server and is independent of the main FastAPI app.
