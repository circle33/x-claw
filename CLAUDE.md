# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

x-claw 是一个基于 FastAPI 的 REST API 服务，提供 Twitter/X 和 Reddit 数据查询接口。Twitter/X 通过 twscrape 库实现，Reddit 通过 httpx 直接调用 `.json` 端点实现。启动时从 `cookies/` 目录加载浏览器导出的 cookie 文件进行认证。

## Development Setup

- **Python**: 3.12+ (managed via uv)
- **Package manager**: [uv](https://docs.astral.sh/uv/)
- **Install dependencies**: `uv sync`
- **Run**: `uv run uvicorn app.main:app --reload`
- **API docs**: 启动后访问 `http://localhost:8000/docs`

### 环境变量（`.env` 文件）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `COOKIES_DIR` | `./cookies` | cookie 文件目录 |
| `DB_PATH` | `./accounts.db` | twscrape 账号数据库路径 |
| `PROXY` | 读取系统 `https_proxy`/`HTTPS_PROXY` | 代理地址 |

## Architecture

```
app/
├── api/v1/endpoints/    # API 路由（tweets, users, trends, reddit_posts, reddit_users, reddit_subreddit）
├── core/                # 配置（config.py）+ twscrape 实例管理（twscrape.py）+ Reddit 客户端（reddit.py）
├── schemas/             # Pydantic 响应模型
└── main.py              # 应用入口（lifespan 加载 cookies）
```

### Twitter/X 模块
- twscrape API 实例通过 `app.state.twscrape_api` 存储，`Depends(get_api)` 注入
- Cookie 文件格式：`cookies/x/@用户名.json`，浏览器导出的 JSON 数组
- `load_accounts()` 从文件名提取用户名，解析 `auth_token` + `ct0` 拼接 cookie 字符串，调用 `api.pool.add_account()` 后 `login_all()`
- 账号管理通过 twscrape CLI，不通过 API

### Reddit 模块
- `RedditClient` 通过 `app.state.reddit_client` 存储，`Depends(get_reddit_client)` 注入
- Cookie 文件格式：`cookies/reddit/用户名.json`，浏览器导出的 JSON 数组（所有 cookie 合并到同一个 httpx 客户端）
- 通过 Reddit Web 端 `.json` 后缀端点获取数据，无需 OAuth；使用 `fake-useragent` 随机 UA

### API 端点一览（前缀 `/api/v1`）

| 模块 | 端点 |
|------|------|
| tweets | `GET /tweets/search`, `GET /tweets/{id}`, `GET /tweets/{id}/replies`, `GET /tweets/{id}/retweeters` |
| users | `GET /users/username/{username}`, `GET /users/{id}`, `GET /users/{id}/tweets`, `GET /users/{id}/followers`, `GET /users/{id}/following` |
| trends | `GET /trends/{category}` |
| reddit-posts | `GET /reddit/posts/search`, `GET /reddit/posts/{subreddit}/{post_id}`, `GET /reddit/posts/{subreddit}/{post_id}/comments` |
| reddit-users | `GET /reddit/users/{username}`, `GET /reddit/users/{username}/posts`, `GET /reddit/users/{username}/comments` |
| reddit-subreddit | `GET /reddit/subreddit/{name}`, `GET /reddit/subreddit/popular` |

### 数据解析模式
- Twitter 端点直接调用 twscrape 对象的 `.dict()` 方法返回
- Reddit 端点在各 endpoint 文件内用 `_parse_post()` / `_parse_comment()` 手动从原始 JSON 提取字段，评论支持递归嵌套解析
