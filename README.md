# x-claw

基于 FastAPI 的多平台社交媒体数据查询 REST API，无需官方 API Key，通过浏览器 Cookie 认证。

| 平台 | 实现方式 |
|------|----------|
| Twitter / X | [twscrape](https://github.com/vladkens/twscrape) |
| Reddit | httpx + `.json` 端点 |
| Bilibili | httpx + WBI 签名 |
| 微博 Weibo | httpx（m.weibo.cn） |
| 快手 Kuaishou | httpx + GraphQL |
| 小红书 XHS | httpx + [xhshow](https://github.com/ReaJason/xhs) 签名 |
| 抖音 Douyin | httpx + JS execjs 签名 |
| 知乎 Zhihu | httpx + JS execjs 签名 |

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

将浏览器导出的 Cookie JSON 数组文件放入对应目录，文件名任意（如 `账号名.json`）：

| 平台 | 目录 | 说明 |
|------|------|------|
| Twitter / X | `cookies/x/` | 需含 `auth_token` 和 `ct0` |
| Reddit | `cookies/reddit/` | 可选，匿名也可访问大部分接口 |
| Bilibili | `cookies/bilibili/` | 需含 `SESSDATA` |
| 微博 | `cookies/weibo/` | 需含 `SUB` |
| 快手 | `cookies/kuaishou/` | 需含 `passToken` |
| 小红书 | `cookies/xhs/` | 需含 `a1`、`web_session` |
| 抖音 | `cookies/douyin/` | 需含 `sessionid` |
| 知乎 | `cookies/zhihu/` | 需含 `z_c0` |

推荐使用 [EditThisCookie](https://www.editthiscookie.com/) 等浏览器扩展导出 JSON 格式 Cookie。

## 环境变量

在项目根目录创建 `.env` 文件：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `COOKIES_DIR` | `./cookies` | Cookie 文件根目录 |
| `DB_PATH` | `./accounts.db` | twscrape 账号数据库路径 |
| `PROXY` | 系统 `https_proxy` / `HTTPS_PROXY` | 代理地址（访问国内平台必填） |

> **注意**：Bilibili、微博、快手、小红书、抖音、知乎均为国内平台，境外服务器需配置 `PROXY`。

## API 端点

所有端点均以 `/api/v1` 为前缀，完整文档见 `/docs`。

### Twitter / X

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

### Bilibili

| 端点 | 说明 |
|------|------|
| `GET /bilibili/videos/search?keyword=` | 搜索视频 |
| `GET /bilibili/videos/{bvid}` | 获取视频详情 |
| `GET /bilibili/videos/{bvid}/comments` | 获取视频评论 |
| `GET /bilibili/users/{mid}` | 获取用户信息 |
| `GET /bilibili/users/{mid}/videos` | 获取用户投稿列表 |

### 微博 Weibo

| 端点 | 说明 |
|------|------|
| `GET /weibo/posts/search?keyword=` | 搜索微博 |
| `GET /weibo/posts/{mid}/comments` | 获取微博评论 |
| `GET /weibo/users/{user_id}` | 获取用户信息 |
| `GET /weibo/users/{user_id}/posts` | 获取用户微博列表 |

### 快手 Kuaishou

| 端点 | 说明 |
|------|------|
| `GET /kuaishou/videos/search?keyword=` | 搜索视频 |
| `GET /kuaishou/videos/{photo_id}` | 获取视频详情 |
| `GET /kuaishou/videos/{photo_id}/comments` | 获取视频评论 |
| `GET /kuaishou/users/{user_id}` | 获取用户信息 |
| `GET /kuaishou/users/{user_id}/videos` | 获取用户视频列表 |

### 小红书 XHS

| 端点 | 说明 |
|------|------|
| `GET /xhs/notes/search?keyword=` | 搜索笔记 |
| `GET /xhs/notes/{note_id}/comments?xsec_token=` | 获取笔记评论 |
| `GET /xhs/users/{user_id}/notes` | 获取用户笔记列表 |

### 抖音 Douyin

| 端点 | 说明 |
|------|------|
| `GET /douyin/videos/search?keyword=` | 搜索视频 |
| `GET /douyin/videos/{aweme_id}` | 获取视频详情 |
| `GET /douyin/videos/{aweme_id}/comments` | 获取视频评论 |
| `GET /douyin/users/{sec_user_id}` | 获取用户信息 |
| `GET /douyin/users/{sec_user_id}/videos` | 获取用户视频列表 |

### 知乎 Zhihu

| 端点 | 说明 |
|------|------|
| `GET /zhihu/search?keyword=` | 搜索内容（回答/文章/问题） |
| `GET /zhihu/answers/{answer_id}/comments` | 获取回答评论 |
| `GET /zhihu/users/{url_token}/answers` | 获取用户回答列表 |
| `GET /zhihu/users/{url_token}/articles` | 获取用户文章列表 |

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
- [httpx](https://www.python-httpx.org/) — 异步 HTTP 客户端
- [xhshow](https://github.com/ReaJason/xhs) — 小红书请求签名
- [PyExecJS](https://github.com/doloopwhile/PyExecJS) — 执行 JS 签名（抖音/知乎）
- [mitmproxy-mcp](https://github.com/snapspecter/mitmproxy-mcp) — MCP 代理控制服务器
- [uv](https://docs.astral.sh/uv/) — 依赖管理
