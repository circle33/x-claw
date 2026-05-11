from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from twscrape import API

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.reddit import RedditClient
from app.core.twscrape import load_accounts


@asynccontextmanager
async def lifespan(app: FastAPI):
    api = API(settings.DB_PATH, proxy=settings.PROXY)
    await load_accounts(api)
    app.state.twscrape_api = api

    reddit_client = RedditClient()
    await reddit_client.init()
    app.state.reddit_client = reddit_client

    yield
    await reddit_client.close()


app = FastAPI(
    title="x-claw",
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
