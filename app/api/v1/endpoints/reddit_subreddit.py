from fastapi import APIRouter, Depends, Path, Query

from app.core.reddit import RedditClient, get_reddit_client
from app.schemas.reddit_post import RedditPostResponse

router = APIRouter(prefix="/reddit", tags=["Reddit"])


def _parse_post(child: dict) -> dict:
    d = child["data"]
    return {
        "id": d["id"],
        "title": d["title"],
        "selftext": d.get("selftext"),
        "subreddit": d["subreddit"],
        "author": d.get("author"),
        "score": d.get("score", 0),
        "upvote_ratio": d.get("upvote_ratio", 0.0),
        "num_comments": d.get("num_comments", 0),
        "created_utc": d.get("created_utc", 0),
        "url": d.get("url", ""),
        "permalink": d.get("permalink", ""),
        "link_flair_text": d.get("link_flair_text"),
        "over_18": d.get("over_18", False),
        "thumbnail": d.get("thumbnail"),
        "is_self": d.get("is_self", True),
    }


@router.get(
    "/subreddit/{subreddit}",
    response_model=list[RedditPostResponse],
    summary="获取子版块帖子",
    description="获取指定子版块的帖子列表，按热度排序。"
    "例如：python、worldnews、gaming 等。",
)
async def get_subreddit_posts(
    subreddit: str = Path(..., description="子版块名称，例如 python"),
    limit: int = Query(20, ge=1, le=100, description="返回结果数量，1-100"),
    client: RedditClient = Depends(get_reddit_client),
):
    children = await client.get_subreddit(subreddit, limit=limit)
    return [_parse_post(c) for c in children if c["kind"] == "t3"]


@router.get(
    "/popular",
    response_model=list[RedditPostResponse],
    summary="获取热门帖子",
    description="获取 Reddit 首页热门帖子列表，聚合自全站各子版块。",
)
async def get_popular(
    limit: int = Query(20, ge=1, le=100, description="返回结果数量，1-100"),
    client: RedditClient = Depends(get_reddit_client),
):
    children = await client.get_popular(limit=limit)
    return [_parse_post(c) for c in children if c["kind"] == "t3"]
