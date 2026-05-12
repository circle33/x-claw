from fastapi import APIRouter

from app.api.v1.endpoints import (
    bilibili_users,
    bilibili_videos,
    douyin_users,
    douyin_videos,
    kuaishou_users,
    kuaishou_videos,
    reddit_posts,
    reddit_subreddit,
    reddit_users,
    trends,
    tweets,
    users,
    weibo_posts,
    weibo_users,
    xhs_notes,
    xhs_users,
    zhihu_content,
    zhihu_users,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(tweets.router)
api_router.include_router(users.router)
api_router.include_router(trends.router)
api_router.include_router(reddit_posts.router)
api_router.include_router(reddit_users.router)
api_router.include_router(reddit_subreddit.router)
api_router.include_router(bilibili_videos.router)
api_router.include_router(bilibili_users.router)
api_router.include_router(weibo_posts.router)
api_router.include_router(weibo_users.router)
api_router.include_router(kuaishou_videos.router)
api_router.include_router(kuaishou_users.router)
api_router.include_router(xhs_notes.router)
api_router.include_router(xhs_users.router)
api_router.include_router(douyin_videos.router)
api_router.include_router(douyin_users.router)
api_router.include_router(zhihu_content.router)
api_router.include_router(zhihu_users.router)
