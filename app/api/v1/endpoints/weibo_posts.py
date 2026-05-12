from fastapi import APIRouter, Depends, Query

from app.core.weibo import WeiboClient, get_weibo_client
from app.schemas.weibo import WeiboCommentPageResponse, WeiboCommentResponse, WeiboPostResponse

router = APIRouter(prefix="/weibo/posts", tags=["微博 Weibo"])


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


def _parse_comment(c: dict) -> dict:
    user = c.get("user") or {}
    return {
        "id": str(c.get("id", "")),
        "text": c.get("text", ""),
        "user_name": user.get("screen_name", ""),
        "user_id": str(user.get("id", "")),
        "like_count": c.get("like_count", 0),
        "created_at": c.get("created_at", ""),
        "replies": [_parse_comment(r) for r in (c.get("comments") or [])],
    }


@router.get("/search", response_model=list[WeiboPostResponse])
async def search_posts(
    keyword: str = Query(..., description="搜索关键词"),
    page: int = Query(1, ge=1),
    search_type: int = Query(1, description="搜索类型：1=综合"),
    client: WeiboClient = Depends(get_weibo_client),
):
    data = await client.search_posts(keyword, page=page, search_type=search_type)
    cards = data.get("cards", [])
    posts = []
    for card in cards:
        if card.get("card_type") == 9:
            parsed = _parse_post(card)
            if parsed:
                posts.append(WeiboPostResponse(**parsed))
    return posts


@router.get("/{mid}/comments", response_model=WeiboCommentPageResponse)
async def get_post_comments(
    mid: str,
    max_id: int = Query(0, ge=0, description="翻页游标，首次传 0"),
    client: WeiboClient = Depends(get_weibo_client),
):
    data = await client.get_post_comments(mid, max_id=max_id)
    comments = [WeiboCommentResponse(**_parse_comment(c)) for c in (data.get("data") or [])]
    return WeiboCommentPageResponse(
        comments=comments,
        max_id=data.get("max_id", 0),
        max_id_type=data.get("max_id_type", 0),
    )
