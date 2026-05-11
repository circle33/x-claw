from fastapi import APIRouter, Depends, Path, Query

from app.core.reddit import RedditClient, get_reddit_client
from app.schemas.reddit_post import RedditCommentResponse, RedditPostResponse

router = APIRouter(prefix="/reddit/posts", tags=["reddit-posts"])


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
    "/search",
    response_model=list[RedditPostResponse],
    summary="搜索 Reddit 帖子",
    description="根据关键词搜索 Reddit 帖子。"
    "支持排序方式：relevance（相关性）、hot（热度）、top（最高）、new（最新）。"
    "返回匹配的帖子列表。",
)
async def search_posts(
    query: str = Query(..., description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回结果数量，1-100"),
    sort: str = Query(
        "relevance",
        description="排序方式：relevance/hot/top/new",
    ),
    client: RedditClient = Depends(get_reddit_client),
):
    children = await client.search(query, limit=limit, sort=sort)
    return [_parse_post(c) for c in children if c["kind"] == "t3"]


@router.get(
    "/{subreddit}/{post_id}",
    response_model=RedditPostResponse,
    summary="获取帖子详情",
    description="根据 subreddit 和帖子 ID 获取帖子详情。"
    "如果帖子不存在，返回 404。",
)
async def get_post(
    subreddit: str = Path(..., description="子版块名称"),
    post_id: str = Path(..., description="帖子 ID"),
    client: RedditClient = Depends(get_reddit_client),
):
    data = await client.get_post(subreddit, post_id)
    if not data or not data[0]["data"]["children"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Post not found")
    return _parse_post(data[0]["data"]["children"][0])


@router.get(
    "/{subreddit}/{post_id}/comments",
    response_model=list[RedditCommentResponse],
    summary="获取帖子评论",
    description="获取指定帖子下的评论列表，支持嵌套回复。"
    "默认按热度排序，最多返回 limit 条顶级评论。",
)
async def get_post_comments(
    subreddit: str = Path(..., description="子版块名称"),
    post_id: str = Path(..., description="帖子 ID"),
    limit: int = Query(20, ge=1, le=100, description="返回结果数量，1-100"),
    client: RedditClient = Depends(get_reddit_client),
):
    children = await client.get_post_comments(subreddit, post_id, limit=limit)
    return [_parse_comment(c) for c in children if c["kind"] == "t1"]
