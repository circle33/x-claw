from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.core.reddit import RedditClient, get_reddit_client
from app.schemas.reddit_post import RedditCommentResponse, RedditPostResponse
from app.schemas.reddit_user import RedditUserResponse

router = APIRouter(prefix="/reddit/users", tags=["reddit-users"])


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


def _parse_comment(child: dict) -> dict:
    d = child["data"]
    replies: list[dict] = []
    raw_replies = d.get("replies")
    if isinstance(raw_replies, dict):
        for rc in raw_replies["data"]["children"]:
            if rc["kind"] == "t1":
                replies.append(_parse_comment(rc))
    return {
        "id": d["id"],
        "author": d.get("author"),
        "body": d.get("body", ""),
        "score": d.get("score", 0),
        "created_utc": d.get("created_utc", 0),
        "permalink": d.get("permalink", ""),
        "replies": replies,
    }


@router.get(
    "/{username}",
    response_model=RedditUserResponse,
    summary="查询 Reddit 用户",
    description="根据用户名获取 Reddit 用户信息，"
    "包括 karma、认证状态、注册时间等。如果用户不存在，返回 404。",
)
async def get_user(
    username: str = Path(..., description="Reddit 用户名"),
    client: RedditClient = Depends(get_reddit_client),
):
    data = await client.get_user(username)
    if not data:
        raise HTTPException(status_code=404, detail="User not found")
    subreddit = data.get("subreddit") or {}
    return {
        "id": data["id"],
        "username": data["name"],
        "displayname": subreddit.get("title"),
        "description": subreddit.get("public_description"),
        "link_karma": data.get("link_karma", 0),
        "comment_karma": data.get("comment_karma", 0),
        "total_karma": data.get("total_karma", 0),
        "created_utc": data.get("created_utc"),
        "is_verified": data.get("verified", False),
        "has_verified_email": data.get("has_verified_email", False),
        "is_gold": data.get("is_gold", False),
    }


@router.get(
    "/{username}/posts",
    response_model=list[RedditPostResponse],
    summary="获取用户帖子",
    description="获取指定 Reddit 用户发布的帖子列表，按时间倒序排列。",
)
async def get_user_posts(
    username: str = Path(..., description="Reddit 用户名"),
    limit: int = Query(20, ge=1, le=100, description="返回结果数量，1-100"),
    client: RedditClient = Depends(get_reddit_client),
):
    children = await client.get_user_posts(username, limit=limit)
    return [_parse_post(c) for c in children if c["kind"] == "t3"]


@router.get(
    "/{username}/comments",
    response_model=list[RedditCommentResponse],
    summary="获取用户评论",
    description="获取指定 Reddit 用户发布的评论列表，按时间倒序排列。",
)
async def get_user_comments(
    username: str = Path(..., description="Reddit 用户名"),
    limit: int = Query(20, ge=1, le=100, description="返回结果数量，1-100"),
    client: RedditClient = Depends(get_reddit_client),
):
    children = await client.get_user_comments(username, limit=limit)
    return [_parse_comment(c) for c in children if c["kind"] == "t1"]
