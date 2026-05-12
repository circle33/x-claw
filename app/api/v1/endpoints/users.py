from fastapi import APIRouter, Depends, HTTPException, Path, Query
from twscrape import API, gather

from app.core.twscrape import get_api
from app.schemas.tweet import TweetResponse

router = APIRouter(prefix="/users", tags=["Twitter / X"])


@router.get(
    "/username/{username}",
    response_model=dict,
    summary="按用户名查询用户",
    description="根据 Twitter/X 用户名（不含 @）获取用户详细信息，"
    "包括用户 ID、昵称、简介、粉丝数、关注数、推文数、认证状态、注册时间等。"
    "如果用户不存在，返回 404。",
)
async def user_by_login(
    username: str = Path(..., description="Twitter 用户名，不含 @，例如 elonmusk"),
    api: API = Depends(get_api),
):
    user = await api.user_by_login(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.dict()


@router.get(
    "/{user_id}",
    response_model=dict,
    summary="按用户 ID 查询用户",
    description="根据 Twitter/X 数字用户 ID 获取用户详细信息，"
    "包括用户名、昵称、简介、粉丝数、关注数、推文数、认证状态、注册时间等。"
    "如果用户不存在，返回 404。",
)
async def user_by_id(
    user_id: int = Path(..., description="Twitter 用户 ID，例如 44196397"),
    api: API = Depends(get_api),
):
    user = await api.user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.dict()


@router.get(
    "/{user_id}/tweets",
    response_model=list[TweetResponse],
    summary="获取用户推文",
    description="获取指定用户发布的推文列表（不含回复），按时间倒序排列。"
    "注意：Twitter 平台限制最多返回约 3200 条推文。"
    "每条推文包含内容、发布时间、互动数据（点赞、转发、回复、浏览量）。",
)
async def user_tweets(
    user_id: int = Path(..., description="Twitter 用户 ID"),
    limit: int = Query(20, ge=1, le=100, description="返回结果数量，1-100"),
    api: API = Depends(get_api),
):
    tweets = await gather(api.user_tweets(user_id, limit=limit))
    return [t.dict() for t in tweets]


@router.get(
    "/{user_id}/followers",
    response_model=list[dict],
    summary="获取用户粉丝列表",
    description="获取关注指定用户的粉丝列表，包含每个粉丝的用户名、昵称、"
    "简介、粉丝数、认证状态等个人信息。",
)
async def followers(
    user_id: int = Path(..., description="Twitter 用户 ID"),
    limit: int = Query(20, ge=1, le=100, description="返回结果数量，1-100"),
    api: API = Depends(get_api),
):
    users = await gather(api.followers(user_id, limit=limit))
    return [u.dict() for u in users]


@router.get(
    "/{user_id}/following",
    response_model=list[dict],
    summary="获取用户关注列表",
    description="获取指定用户关注的人的列表，包含每个用户的用户名、昵称、"
    "简介、粉丝数、认证状态等个人信息。",
)
async def following(
    user_id: int = Path(..., description="Twitter 用户 ID"),
    limit: int = Query(20, ge=1, le=100, description="返回结果数量，1-100"),
    api: API = Depends(get_api),
):
    users = await gather(api.following(user_id, limit=limit))
    return [u.dict() for u in users]
