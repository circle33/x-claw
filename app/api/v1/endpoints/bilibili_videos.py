from fastapi import APIRouter, Depends, Query

from app.core.bilibili import BilibiliClient, get_bilibili_client
from app.schemas.bilibili import (
    BilibiliCommentPageResponse,
    BilibiliCommentResponse,
    BilibiliVideoDetailResponse,
    BilibiliVideoResponse,
)

router = APIRouter(prefix="/bilibili/videos", tags=["Bilibili"])


def _parse_search_video(item: dict) -> dict:
    pic = item.get("pic", "")
    return {
        "bvid": item["bvid"],
        "aid": item["aid"],
        "title": item.get("title", ""),
        "author": item.get("author", ""),
        "mid": item.get("mid", 0),
        "pic": ("https:" + pic) if pic.startswith("//") else pic,
        "description": item.get("description", ""),
        "play": item.get("play", 0),
        "danmaku": item.get("danmaku", 0),
        "reply": item.get("reply", 0),
        "favorite": item.get("favorites", 0),
        "coin": item.get("coin", 0),
        "share": item.get("share", 0),
        "like": item.get("like", 0),
        "pubdate": item.get("pubdate", 0),
        "duration": item.get("duration", ""),
        "tag": item.get("tag", ""),
    }


def _parse_video_detail(view: dict) -> dict:
    stat = view.get("stat", {})
    owner = view.get("owner", {})
    return {
        "bvid": view["bvid"],
        "aid": view["aid"],
        "title": view.get("title", ""),
        "desc": view.get("desc", ""),
        "pic": view.get("pic", ""),
        "owner_name": owner.get("name", ""),
        "owner_mid": owner.get("mid", 0),
        "view": stat.get("view", 0),
        "danmaku": stat.get("danmaku", 0),
        "reply": stat.get("reply", 0),
        "favorite": stat.get("favorite", 0),
        "coin": stat.get("coin", 0),
        "share": stat.get("share", 0),
        "like": stat.get("like", 0),
        "pubdate": view.get("pubdate", 0),
        "duration": view.get("duration", 0),
        "tname": view.get("tname", ""),
        "tags": [t["tag_name"] for t in view.get("tag", [])],
    }


def _parse_comment(c: dict) -> dict:
    return {
        "rpid": c["rpid"],
        "oid": c.get("oid", 0),
        "mid": c.get("mid", 0),
        "uname": c.get("member", {}).get("uname", ""),
        "content": c.get("content", {}).get("message", ""),
        "like": c.get("like", 0),
        "rcount": c.get("rcount", 0),
        "ctime": c.get("ctime", 0),
        "replies": [_parse_comment(r) for r in (c.get("replies") or [])],
    }


@router.get("/search", response_model=list[BilibiliVideoResponse])
async def search_videos(
    keyword: str = Query(..., description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    client: BilibiliClient = Depends(get_bilibili_client),
):
    data = await client.search_videos(keyword, page=page, page_size=page_size)
    return [_parse_search_video(item) for item in (data.get("result") or [])]


@router.get("/{bvid}", response_model=BilibiliVideoDetailResponse)
async def get_video(
    bvid: str,
    client: BilibiliClient = Depends(get_bilibili_client),
):
    data = await client.get_video_detail(bvid)
    return _parse_video_detail(data["View"])


@router.get("/{bvid}/comments", response_model=BilibiliCommentPageResponse)
async def get_video_comments(
    bvid: str,
    next_page: int = Query(0, ge=0, description="翻页游标，首次请求传 0"),
    client: BilibiliClient = Depends(get_bilibili_client),
):
    detail = await client.get_video_detail(bvid)
    oid = detail["View"]["aid"]
    data = await client.get_video_comments(oid, next_page=next_page)
    cursor = data.get("cursor", {})
    return BilibiliCommentPageResponse(
        comments=[BilibiliCommentResponse(**_parse_comment(c)) for c in (data.get("replies") or [])],
        is_end=cursor.get("is_end", True),
        next_cursor=cursor.get("next", 0),
    )
