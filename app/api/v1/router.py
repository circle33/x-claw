from fastapi import APIRouter

from app.api.v1.endpoints import (
    reddit_posts,
    reddit_subreddit,
    reddit_users,
    tweets,
    trends,
    users,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(tweets.router)
api_router.include_router(users.router)
api_router.include_router(trends.router)
api_router.include_router(reddit_posts.router)
api_router.include_router(reddit_users.router)
api_router.include_router(reddit_subreddit.router)
