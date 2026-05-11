from fastapi import APIRouter, Depends, HTTPException, Path, Query
from twscrape import API, gather

from app.core.twscrape import get_api
from app.schemas.tweet import TweetResponse

router = APIRouter(prefix="/tweets", tags=["tweets"])


@router.get(
    "/search",
    response_model=list[TweetResponse],
    summary="搜索推文",
    description="根据关键词搜索 Twitter/X 推文。支持标准 Twitter 搜索语法，例如："
    "`python lang:en`（语言筛选）、`AI since:2024-01-01`（日期筛选）、"
    "`from:elonmusk`（指定用户）、`cats filter:media`（仅含媒体）。"
    "结果按时间倒序排列。",
)
async def search_tweets(
    query: str = Query(..., description="搜索关键词，支持 Twitter 搜索语法"),
    limit: int = Query(20, ge=1, le=100, description="返回结果数量，1-100"),
    api: API = Depends(get_api),
):
    tweets = await gather(api.search(query, limit=limit))
    return [t.dict() for t in tweets]


@router.get(
    "/{tweet_id}",
    response_model=TweetResponse,
    summary="获取推文详情",
    description="根据推文 ID 获取单条推文的完整信息，包括内容、作者、点赞数、转发数、"
    "回复数、浏览量等。如果推文不存在或已被删除，返回 404。",
)
async def tweet_details(
    tweet_id: int = Path(..., description="推文 ID，例如 1234567890"),
    api: API = Depends(get_api),
):
    tweet = await api.tweet_details(tweet_id)
    if not tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")
    return tweet.dict()


@router.get(
    "/{tweet_id}/replies",
    response_model=list[TweetResponse],
    summary="获取推文回复",
    description="获取指定推文下的回复列表，按时间倒序排列。"
    "包括回复的内容、作者信息、互动数据等。",
)
async def tweet_replies(
    tweet_id: int = Path(..., description="推文 ID"),
    limit: int = Query(20, ge=1, le=100, description="返回结果数量，1-100"),
    api: API = Depends(get_api),
):
    tweets = await gather(api.tweet_replies(tweet_id, limit=limit))
    return [t.dict() for t in tweets]


@router.get(
    "/{tweet_id}/retweeters",
    response_model=list[dict],
    summary="获取转推用户列表",
    description="获取转发了指定推文的用户列表，包含每个用户的个人信息"
    "（用户名、昵称、粉丝数等）。",
)
async def retweeters(
    tweet_id: int = Path(..., description="推文 ID"),
    limit: int = Query(20, ge=1, le=100, description="返回结果数量，1-100"),
    api: API = Depends(get_api),
):
    users = await gather(api.retweeters(tweet_id, limit=limit))
    return [u.dict() for u in users]
