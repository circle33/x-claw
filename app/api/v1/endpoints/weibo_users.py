from fastapi import APIRouter, Depends, Query

from app.core.weibo import WeiboClient, get_weibo_client
from app.schemas.weibo import WeiboPostResponse, WeiboUserResponse

router = APIRouter(prefix="/weibo/users", tags=["微博 Weibo"])


def _parse_user(info: dict) -> dict:
    return {
        "id": str(info.get("id", "")),
        "screen_name": info.get("screen_name", ""),
        "description": info.get("description", ""),
        "followers_count": info.get("followers_count", 0),
        "follow_count": info.get("follow_count", 0),
        "statuses_count": info.get("statuses_count", 0),
        "profile_image_url": info.get("profile_image_url", ""),
    }


def _parse_post(card: dict) -> dict | None:
    mblog = card.get("mblog")
    if not mblog:
        return None
    user = mblog.get("user") or {}
    return {
        "mid": mblog.get("mid", ""),
        "bid": mblog.get("bid", ""),
        "text": mblog.get("text", ""),
        "user_name": user.get("screen_name", ""),
        "user_id": str(user.get("id", "")),
        "reposts_count": mblog.get("reposts_count", 0),
        "comments_count": mblog.get("comments_count", 0),
        "attitudes_count": mblog.get("attitudes_count", 0),
        "created_at": mblog.get("created_at", ""),
    }


@router.get("/{user_id}", response_model=WeiboUserResponse)
async def get_user(
    user_id: str,
    client: WeiboClient = Depends(get_weibo_client),
):
    data = await client.get_user_info(user_id)
    info = data.get("userInfo", {})
    return WeiboUserResponse(**_parse_user(info))


@router.get("/{user_id}/posts", response_model=list[WeiboPostResponse])
async def get_user_posts(
    user_id: str,
    container_id: str = Query(..., description="用户容器 ID，从 GET /weibo/users/{user_id} 返回的 tabsInfo 中获取"),
    since_id: str = Query("", description="翻页游标"),
    client: WeiboClient = Depends(get_weibo_client),
):
    data = await client.get_user_posts(container_id, since_id=since_id)
    cards = data.get("cards", [])
    posts = []
    for card in cards:
        if card.get("card_type") == 9:
            parsed = _parse_post(card)
            if parsed:
                posts.append(WeiboPostResponse(**parsed))
    return posts
