from fastapi import APIRouter, Depends, Query

from app.core.bilibili import BilibiliClient, get_bilibili_client
from app.schemas.bilibili import (
    BilibiliUserResponse,
    BilibiliUserVideosResponse,
    BilibiliVideoResponse,
)

router = APIRouter(prefix="/bilibili/users", tags=["Bilibili"])


def _parse_user(data: dict) -> dict:
    return {
        "mid": data["mid"],
        "name": data.get("name", ""),
        "sex": data.get("sex", ""),
        "face": data.get("face", ""),
        "sign": data.get("sign", ""),
        "level": data.get("level", 0),
        "following": data.get("following", 0),
        "follower": data.get("follower", 0),
        "video_count": data.get("video_count", 0),
    }


def _parse_user_video(item: dict, mid: int) -> dict:
    pic = item.get("pic", "")
    return {
        "bvid": item["bvid"],
        "aid": item["aid"],
        "title": item.get("title", ""),
        "author": item.get("author", ""),
        "mid": mid,
        "pic": ("https:" + pic) if pic.startswith("//") else pic,
        "description": item.get("description", ""),
        "play": item.get("play", 0),
        "danmaku": item.get("video_review", 0),
        "reply": item.get("comment", 0),
        "favorite": item.get("favorites", 0),
        "coin": 0,
        "share": 0,
        "like": item.get("like", 0),
        "pubdate": item.get("created", 0),
        "duration": item.get("length", ""),
        "tag": "",
    }


@router.get("/{mid}", response_model=BilibiliUserResponse)
async def get_user(
    mid: int,
    client: BilibiliClient = Depends(get_bilibili_client),
):
    data = await client.get_user_info(mid)
    return _parse_user(data)


@router.get("/{mid}/videos", response_model=BilibiliUserVideosResponse)
async def get_user_videos(
    mid: int,
    pn: int = Query(1, ge=1, description="页码"),
    ps: int = Query(30, ge=1, le=50, description="每页数量"),
    client: BilibiliClient = Depends(get_bilibili_client),
):
    data = await client.get_user_videos(mid, pn=pn, ps=ps)
    vlist = data.get("list", {}).get("vlist") or []
    return BilibiliUserVideosResponse(
        mid=mid,
        total=data.get("page", {}).get("count", len(vlist)),
        videos=[BilibiliVideoResponse(**_parse_user_video(v, mid)) for v in vlist],
    )
