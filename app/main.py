import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from twscrape import API

from app.api.v1.router import api_router
from app.core.account_pool import PlatformAccountPool
from app.core.bilibili import BilibiliClient
from app.core.config import settings
from app.core.douyin import DouyinClient
from app.core.kuaishou import KuaishouClient
from app.core.reddit import RedditClient
from app.core.twscrape import load_accounts
from app.core.weibo import WeiboClient
from app.core.xhs import XhsClient
from app.core.zhihu import ZhihuClient


class _UTF8JSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(content, ensure_ascii=False, allow_nan=False).encode("utf-8")


@asynccontextmanager
async def lifespan(app: FastAPI):
    api = API(settings.DB_PATH, proxy=settings.PROXY)
    await load_accounts(api)
    app.state.twscrape_api = api

    pool = PlatformAccountPool(settings.PLATFORM_DB_PATH)
    await pool.init()
    app.state.account_pool = pool

    reddit_client = RedditClient()
    await reddit_client.init()
    app.state.reddit_client = reddit_client

    bilibili_client = BilibiliClient(pool)
    await bilibili_client.init()
    app.state.bilibili_client = bilibili_client

    weibo_client = WeiboClient(pool)
    await weibo_client.init()
    app.state.weibo_client = weibo_client

    kuaishou_client = KuaishouClient(pool)
    await kuaishou_client.init()
    app.state.kuaishou_client = kuaishou_client

    xhs_client = XhsClient(pool)
    await xhs_client.init()
    app.state.xhs_client = xhs_client

    douyin_client = DouyinClient(pool)
    await douyin_client.init()
    app.state.douyin_client = douyin_client

    zhihu_client = ZhihuClient(pool)
    await zhihu_client.init()
    app.state.zhihu_client = zhihu_client

    yield
    await reddit_client.close()
    await bilibili_client.close()
    await weibo_client.close()
    await kuaishou_client.close()
    await xhs_client.close()
    await douyin_client.close()
    await zhihu_client.close()
    await pool.close()


_TAGS = [
    {"name": "Twitter / X", "description": "推文、用户、热搜趋势（via twscrape）"},
    {"name": "Reddit", "description": "帖子、评论、用户、Subreddit（via httpx）"},
    {"name": "Bilibili", "description": "视频搜索、详情、评论、用户（WBI 签名）"},
    {"name": "微博 Weibo", "description": "搜索、评论、用户（需 Cookie）"},
    {"name": "快手 Kuaishou", "description": "视频搜索、评论、用户（GraphQL，需 Cookie）"},
    {"name": "小红书 XHS", "description": "笔记搜索、评论、用户（xhshow 签名，需 Cookie）"},
    {"name": "抖音 Douyin", "description": "视频搜索、评论、用户（JS 签名，需 Cookie）"},
    {"name": "知乎 Zhihu", "description": "搜索、回答、文章、评论（JS 签名，需 Cookie）"},
    {"name": "Accounts", "description": "查看各平台账号状态（cookie 使用情况、是否 active）"},
]

app = FastAPI(
    title="x-claw",
    default_response_class=_UTF8JSONResponse,
    openapi_tags=_TAGS,
    version="0.1.0",
    description="基于 twscrape 的 Twitter/X 数据查询 API，以及基于 httpx 的 Reddit 数据查询 API。"
    "提供推文/帖子搜索、用户信息查询、评论获取、热门趋势等接口。"
    "启动时自动从 cookies/ 目录加载账号。",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
