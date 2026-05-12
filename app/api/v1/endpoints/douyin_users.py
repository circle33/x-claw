from fastapi import APIRouter, Depends, Query

from app.core.douyin import DouyinClient, get_douyin_client
from app.schemas.douyin import DouyinUserResponse, DouyinUserVideosResponse, DouyinVideoResponse

router = APIRouter(prefix="/douyin/users", tags=["抖音 Douyin"])


def _parse_user(u: dict) -> dict:
    avatar = u.get("avatar_thumb") or {}
    return {
        "uid": u.get("uid", ""),
        "sec_uid": u.get("sec_uid", ""),
        "nickname": u.get("nickname", ""),
        "signature": u.get("signature", ""),
        "follower_count": u.get("follower_count", 0),
        "following_count": u.get("following_count", 0),
        "aweme_count": u.get("aweme_count", 0),
        "avatar_url": avatar.get("url_list", [""])[0] if avatar.get("url_list") else "",
    }


def _parse_video(item: dict) -> dict:
    stat = item.get("statistics") or {}
    author = item.get("author") or {}
    cover = item.get("video", {}).get("cover", {})
    cover_url = cover.get("url_list", [""])[0] if cover.get("url_list") else ""
    return {
        "aweme_id": item.get("aweme_id", ""),
        "desc": item.get("desc", ""),
        "author_name": author.get("nickname", ""),
        "sec_uid": author.get("sec_uid", ""),
        "digg_count": stat.get("digg_count", 0),
        "comment_count": stat.get("comment_count", 0),
        "share_count": stat.get("share_count", 0),
        "collect_count": stat.get("collect_count", 0),
        "play_count": stat.get("play_count", 0),
        "create_time": item.get("create_time", 0),
        "cover_url": cover_url,
    }


@router.get("/{sec_user_id}", response_model=DouyinUserResponse)
async def get_user(
    sec_user_id: str,
    client: DouyinClient = Depends(get_douyin_client),
):
    data = await client.get_user_info(sec_user_id)
    u = data.get("user", {})
    return DouyinUserResponse(**_parse_user(u))


@router.get("/{sec_user_id}/videos", response_model=DouyinUserVideosResponse)
async def get_user_videos(
    sec_user_id: str,
    max_cursor: int = Query(0, ge=0, description="翻页游标"),
    count: int = Query(18, ge=1, le=35),
    client: DouyinClient = Depends(get_douyin_client),
):
    data = await client.get_user_videos(sec_user_id, max_cursor=max_cursor, count=count)
    videos = [DouyinVideoResponse(**_parse_video(v)) for v in (data.get("aweme_list") or [])]
    return DouyinUserVideosResponse(
        sec_uid=sec_user_id,
        videos=videos,
        has_more=bool(data.get("has_more", 0)),
        max_cursor=data.get("max_cursor", 0),
    )
