from fastapi import APIRouter, Depends, Query

from app.core.douyin import DouyinClient, get_douyin_client
from app.schemas.douyin import (
    DouyinCommentPageResponse,
    DouyinCommentResponse,
    DouyinVideoDetailResponse,
    DouyinVideoResponse,
)

router = APIRouter(prefix="/douyin/videos", tags=["抖音 Douyin"])


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


def _parse_video_detail(item: dict) -> dict:
    base = _parse_video(item)
    play_addr = item.get("video", {}).get("play_addr", {})
    url_list = play_addr.get("url_list", [])
    base["video_url"] = url_list[0] if url_list else ""
    return base


def _parse_comment(c: dict) -> dict:
    user = c.get("user") or {}
    return {
        "cid": c.get("cid", ""),
        "text": c.get("text", ""),
        "user_name": user.get("nickname", ""),
        "uid": user.get("uid", ""),
        "digg_count": c.get("digg_count", 0),
        "create_time": c.get("create_time", 0),
        "reply_comment_total": c.get("reply_comment_total", 0),
    }


@router.get("/search", response_model=list[DouyinVideoResponse])
async def search_videos(
    keyword: str = Query(..., description="搜索关键词"),
    offset: int = Query(0, ge=0, description="偏移量"),
    count: int = Query(10, ge=1, le=20),
    client: DouyinClient = Depends(get_douyin_client),
):
    data = await client.search_videos(keyword, offset=offset, count=count)
    items = data.get("data") or []
    results = []
    for item in items:
        aweme = item.get("aweme_info") or item
        if aweme.get("aweme_id"):
            results.append(DouyinVideoResponse(**_parse_video(aweme)))
    return results


@router.get("/{aweme_id}", response_model=DouyinVideoDetailResponse)
async def get_video(
    aweme_id: str,
    client: DouyinClient = Depends(get_douyin_client),
):
    data = await client.get_video_detail(aweme_id)
    item = data.get("aweme_detail", {})
    return DouyinVideoDetailResponse(**_parse_video_detail(item))


@router.get("/{aweme_id}/comments", response_model=DouyinCommentPageResponse)
async def get_video_comments(
    aweme_id: str,
    cursor: int = Query(0, ge=0, description="翻页游标"),
    count: int = Query(20, ge=1, le=50),
    client: DouyinClient = Depends(get_douyin_client),
):
    data = await client.get_video_comments(aweme_id, cursor=cursor, count=count)
    comments = [DouyinCommentResponse(**_parse_comment(c)) for c in (data.get("comments") or [])]
    return DouyinCommentPageResponse(
        comments=comments,
        has_more=bool(data.get("has_more", 0)),
        cursor=data.get("cursor", 0),
    )
