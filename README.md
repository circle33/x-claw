# x-claw

基于 FastAPI 的 Twitter/X 与 Reddit 数据查询 REST API。Twitter/X 通过 [twscrape](https://github.com/vladkens/twscrape) 实现，Reddit 通过直接调用 `.json` 端点实现，均无需官方 API Key。

## 快速开始

**依赖**：Python 3.12+，[uv](https://docs.astral.sh/uv/)

```bash
git clone <repo>
cd x-claw
uv sync
uv run uvicorn app.main:app --reload
```

启动后访问 `http://localhost:8000/docs` 查看交互式 API 文档。

## Cookie 配置

服务使用浏览器导出的 cookie 进行认证，无需 API Key。

**Twitter/X**：将 cookie 文件放至 `cookies/x/@用户名.json`（浏览器扩展导出的 JSON 数组格式）。

**Reddit**：将 cookie 文件放至 `cookies/reddit/用户名.json`（同上格式）。

可通过 [EditThisCookie](https://www.editthiscookie.com/) 等浏览器扩展导出 cookie。

## 环境变量

可在项目根目录创建 `.env` 文件进行配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `COOKIES_DIR` | `./cookies` | cookie 文件目录 |
| `DB_PATH` | `./accounts.db` | twscrape 账号数据库路径 |
| `PROXY` | 系统 `https_proxy` / `HTTPS_PROXY` | 代理地址（可选） |

## API 端点

所有端点均以 `/api/v1` 为前缀。

### Twitter/X

| 端点 | 说明 |
|------|------|
| `GET /tweets/search?query=&limit=` | 搜索推文 |
| `GET /tweets/{id}` | 获取单条推文 |
| `GET /tweets/{id}/replies` | 获取推文回复 |
| `GET /tweets/{id}/retweeters` | 获取转推用户列表 |
| `GET /users/username/{username}` | 通过用户名查询用户 |
| `GET /users/{id}` | 通过 ID 查询用户 |
| `GET /users/{id}/tweets` | 获取用户推文 |
| `GET /users/{id}/followers` | 获取粉丝列表 |
| `GET /users/{id}/following` | 获取关注列表 |
| `GET /trends/{category}` | 获取热门趋势 |

### Reddit

| 端点 | 说明 |
|------|------|
| `GET /reddit/posts/search?query=` | 搜索帖子 |
| `GET /reddit/posts/{subreddit}/{post_id}` | 获取单个帖子 |
| `GET /reddit/posts/{subreddit}/{post_id}/comments` | 获取帖子评论（支持嵌套） |
| `GET /reddit/users/{username}` | 获取用户信息 |
| `GET /reddit/users/{username}/posts` | 获取用户帖子 |
| `GET /reddit/users/{username}/comments` | 获取用户评论 |
| `GET /reddit/subreddit/{name}` | 获取子版块帖子列表 |
| `GET /reddit/subreddit/popular` | 获取热门子版块帖子 |

## 技术栈

- [FastAPI](https://fastapi.tiangolo.com/) — Web 框架
- [twscrape](https://github.com/vladkens/twscrape) — Twitter/X 数据抓取
- [httpx](https://www.python-httpx.org/) — Reddit 异步 HTTP 客户端
- [uv](https://docs.astral.sh/uv/) — 依赖管理
