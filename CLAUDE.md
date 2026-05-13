# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

x-claw is a FastAPI REST API that proxies social media data from Twitter/X (via twscrape), Reddit (via httpx + `.json` endpoints), and several Chinese platforms (Bilibili, Weibo, Kuaishou, XHS/Xiaohongshu, Douyin, Zhihu). Authentication is cookie-based: browser-exported cookie files are loaded from the `cookies/` directory at startup.

## Development Commands

```bash
uv sync                                        # install dependencies
uv run uvicorn app.main:app --reload           # run dev server (http://localhost:8000/docs)

# twscrape account management (run separately, not through the API)
uv run twscrape accounts                       # list accounts and their login state
uv run twscrape login_all                      # re-authenticate all accounts
```

No test or lint configuration is set up in the project.

The MCP sub-project (`mcp/`) has its own `uv` environment; run `uv sync` inside `mcp/` separately.

### Environment Variables (`.env`)

| Variable | Default | Notes |
|---|---|---|
| `COOKIES_DIR` | `./cookies` | cookie file root |
| `DB_PATH` | `./accounts.db` | twscrape account DB |
| `PLATFORM_DB_PATH` | `./platform_accounts.db` | Chinese platform account DB |
| `REFRESH_EVERY` | `500` | account pool refresh interval |
| `PROXY` | system `https_proxy`/`HTTPS_PROXY` | optional proxy |

## Architecture

FastAPI lifespan initializes all stateful clients at startup, stored on `app.state` and injected with `Depends()`:

- `app.state.twscrape_api` → `Depends(get_api)` in Twitter endpoints
- `app.state.reddit_client` → `Depends(get_reddit_client)` in Reddit endpoints
- `app.state.bilibili_client`, `weibo_client`, `kuaishou_client`, `xhs_client`, `douyin_client`, `zhihu_client` → platform-specific deps

```
app/
├── main.py                  # lifespan: loads cookies, creates all API clients
├── core/
│   ├── config.py            # pydantic-settings (reads .env)
│   ├── twscrape.py          # twscrape API instance + account loader
│   ├── reddit.py            # RedditClient (httpx.AsyncClient wrapper)
│   ├── account_pool.py      # Chinese platform account pool management
│   ├── bilibili.py          # Bilibili client
│   ├── douyin.py            # Douyin client
│   ├── kuaishou.py          # Kuaishou client
│   ├── weibo.py             # Weibo client
│   ├── xhs.py               # Xiaohongshu client
│   └── zhihu.py             # Zhihu client
├── api/v1/
│   ├── router.py            # aggregates all routers under /api/v1
│   └── endpoints/           # one file per platform/resource
└── schemas/                 # Pydantic response models (one file per platform)
```

### Twitter/X Cookie Loading

Cookie files live at `cookies/x/@<username>.json` (browser-exported JSON array).  
`load_accounts()` extracts `auth_token` + `ct0` from each file, calls `api.pool.add_account()`, then `login_all()`.  
Manage accounts via the twscrape CLI — not through this API.

### Reddit Client

Cookie files live at `cookies/reddit/<username>.json`; all are merged into one httpx session.  
Uses Reddit's unauthenticated `.json` suffix endpoints (e.g. `/r/python.json`). No OAuth required.  
User-Agent is randomized via `fake-useragent`.

### Chinese Platform Clients

Each platform (`bilibili`, `weibo`, `kuaishou`, `xhs`, `douyin`, `zhihu`) follows the same pattern:
- A client class in `app/core/<platform>.py` wrapping an async HTTP client
- Cookie files in `cookies/<platform>/` loaded at startup
- Dependency injection via `Depends(get_<platform>_client)` in endpoint files
- Pydantic schemas in `app/schemas/<platform>.py`

#### PooledClient Base Class (account rotation)

All platform clients extend [`PooledClient`](app/core/account_pool.py), which provides:
- **PlatformAccountPool** — SQLite-backed (via aiosqlite) registry of cookie accounts per platform
- **Auto-rotation** — after every request, `_after_request()` increments a counter; accounts cycle to the least-used one after `REFRESH_EVERY` (default 500) requests
- **Auth error recovery** — on 401/403, `_on_auth_error()` marks the account inactive and triggers `_refresh()` to pick a fallback
- **`_refresh()` contract** — each subclass must implement `_refresh()`: re-reads cookie files from disk, picks an active account, creates a fresh `httpx.AsyncClient` with that account's cookies
- **`_try_refresh()`** — safe wrapper that logs a warning instead of crashing when no cookies exist (allows graceful degradation)

Clients call `await self._load_accounts(cookies_dir)` at init to populate the pool, then `await self._try_refresh()` to establish the first session.

#### Platform-Specific Signing

Each platform's `_get()` wraps the raw httpx call with signing and error handling; the wrapper signatures differ slightly:

| Platform | Signing | Cookie file | Notes |
|---|---|---|---|
| Bilibili | WBI (`img_key`+`sub_key` via nav endpoint) | `SESSDATA` | Fetches WBI keys from `/x/web-interface/nav` on refresh, persists updated cookies back via `_save_cookies_to_pool()` |
| Weibo | None (mobile endpoint) | `SUB` | Uses `m.weibo.cn`, checks `body.ok == 1` |
| Kuaishou | GraphQL POST | `passToken` | |
| XHS | xhshow library | `a1`, `web_session` | |
| Douyin | execjs (`libs/douyin.js`) | `sessionid` | Calls `_sign_obj.call("sign_datail"\|"sign_reply", ...)` for `a_bogus` param |
| Zhihu | execjs (`libs/zhihu.js`) | `z_c0` | |

For Douyin and Zhihu, the JS signature files live in [`libs/`](libs/) and are loaded at module import time via `execjs.compile()`. Douyin also merges a large set of common params (`_COMMON_PARAMS`) into every request.

#### Endpoint File Pattern

Each platform splits into separate `_videos`/`_posts` and `_users` endpoint modules (e.g. [`bilibili_videos.py`](app/api/v1/endpoints/bilibili_videos.py) + [`bilibili_users.py`](app/api/v1/endpoints/bilibili_users.py)). Endpoints call into the client class and use local `_parse_*()` functions to extract fields from the raw API response — they rarely return raw API data directly.

### Data Parsing

- Twitter endpoints return twscrape object `.dict()` directly; schemas in `app/schemas/` document shape but are not always enforced as response models.
- Reddit endpoints parse raw JSON manually with `_parse_post()` / `_parse_comment()` inside each endpoint file; comments are parsed recursively.
- Chinese platform endpoints parse platform-specific API responses in their respective client classes.

### Response Encoding

`main.py` uses a custom `JSONResponse` subclass that sets `ensure_ascii=False`, so non-ASCII characters (Chinese text, emoji) are returned as-is rather than `\uXXXX` escaped.

### CORS

`main.py` adds `CORSMiddleware` with `allow_origins=["*"]`. Keep this in mind if adding any authenticated routes.

### API Endpoints (prefix `/api/v1`)

| Router | Endpoints |
|---|---|
| tweets | `GET /tweets/search`, `/tweets/{id}`, `/tweets/{id}/replies`, `/tweets/{id}/retweeters` |
| users | `GET /users/username/{username}`, `/users/{id}`, `/users/{id}/tweets`, `/users/{id}/followers`, `/users/{id}/following` |
| trends | `GET /trends/{category}` |
| reddit-posts | `GET /reddit/posts/search`, `/reddit/posts/{subreddit}/{post_id}`, `/reddit/posts/{subreddit}/{post_id}/comments` |
| reddit-users | `GET /reddit/users/{username}`, `/reddit/users/{username}/posts`, `/reddit/users/{username}/comments` |
| reddit-subreddit | `GET /reddit/subreddit/{name}`, `/reddit/subreddit/popular` |
| accounts | `GET /accounts` — status of all platform accounts (active/inactive, request count, last used, error) |
| bilibili | video search, video details, user profile/videos |
| weibo | post search, post details, user profile/posts |
| kuaishou | video search, video details, user profile/videos |
| xhs | note search, note details, user profile/notes |
| douyin | video search, video details, user profile/videos |
| zhihu | question/answer search, user profile/answers |

## MCP Integration

`mcp/` contains a separate `mitmproxy-mcp` server project (v0.5.1) with its own `pyproject.toml`, tests, and Docker setup. It is wired up in `.mcp.json` as a stdio MCP server and is independent of the main FastAPI app.

The MCP server runs mitmproxy as a programmatic proxy and exposes tools for traffic capture, inspection, replay, fuzzing, and scraper code generation. Its SQLite database stores captured flows; all tools operate on that store.
