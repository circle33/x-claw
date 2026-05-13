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
| accounts | `GET /accounts` — status of loaded twscrape accounts |
| bilibili | video search, video details, user profile/videos |
| weibo | post search, post details, user profile/posts |
| kuaishou | video search, video details, user profile/videos |
| xhs | note search, note details, user profile/notes |
| douyin | video search, video details, user profile/videos |
| zhihu | question/answer search, user profile/answers |

## MCP Integration

`mcp/` contains a separate `mitmproxy-mcp` server project (v0.5.1) with its own `pyproject.toml`, tests, and Docker setup. It is wired up in `.mcp.json` as a stdio MCP server and is independent of the main FastAPI app.

The MCP server runs mitmproxy as a programmatic proxy and exposes tools for traffic capture, inspection, replay, fuzzing, and scraper code generation. Its SQLite database stores captured flows; all tools operate on that store.
