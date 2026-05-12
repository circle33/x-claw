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

## MCP 集成（mitmproxy-mcp）

`mcp/` 目录包含一个独立的 [Model Context Protocol](https://modelcontextprotocol.io/) 服务器，让 LLM（如 Claude）可以直接控制 mitmproxy 代理，实现对 HTTP/HTTPS 流量的完整操作。

### 核心能力

| 分类 | 功能 |
|------|------|
| **代理控制** | 启停代理、设置流量域名过滤范围 |
| **流量分析** | 捕获完整请求/响应（含 header、body、timing）、按域名/方法/关键词搜索 |
| **拦截修改** | 注入 header、正则替换 body、阻断请求，支持 request/response 两个阶段 |
| **隐身重放** | 用 `curl-cffi` 模拟 Chrome/Safari TLS 指纹重发请求，绕过反爬检测 |
| **会话变量** | 从响应中提取 CSRF token 等动态值并在后续重放中自动注入 |
| **数据提取** | 支持 JSONPath 和 CSS Selector 从响应体提取结构化数据 |
| **API 反向工程** | 聚合流量生成 OpenAPI v3 规格文档、识别认证模式 |
| **安全测试** | 对指定参数批量注入 fuzz payload，报告异常响应 |
| **代码生成** | 从抓包流量生成可执行的爬虫代码（支持 curl_cffi / requests / aiohttp / playwright） |

### 接入方式

项目根目录已通过 `.mcp.json` 配置为 Claude Code 的 stdio MCP server，克隆后即可在 Claude Code 中直接使用。

手动配置（Claude Desktop 等客户端）：

```json
{
  "mcpServers": {
    "mitmproxy-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "/path/to/x-claw/mcp", "mitmproxy-mcp"]
    }
  }
}
```

或通过 `uvx` 直接运行发布版：

```json
{
  "mcpServers": {
    "mitmproxy-mcp": {
      "command": "uvx",
      "args": ["mitmproxy-mcp"]
    }
  }
}
```

### 快速上手

```bash
cd mcp
uv sync
uv run mitmproxy-mcp   # 启动 MCP server
```

> 使用 HTTPS 拦截功能前需在浏览器安装 mitmproxy CA 证书，并将浏览器代理设为 `localhost:8080`。

## 技术栈

- [FastAPI](https://fastapi.tiangolo.com/) — Web 框架
- [twscrape](https://github.com/vladkens/twscrape) — Twitter/X 数据抓取
- [httpx](https://www.python-httpx.org/) — Reddit 异步 HTTP 客户端
- [mitmproxy-mcp](https://github.com/snapspecter/mitmproxy-mcp) — MCP 代理控制服务器
- [uv](https://docs.astral.sh/uv/) — 依赖管理
