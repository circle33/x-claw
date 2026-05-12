from fastapi import APIRouter, Depends, Query

from app.core.kuaishou import KuaishouClient, get_kuaishou_client
from app.schemas.kuaishou import KuaishouCommentPageResponse, KuaishouCommentResponse, KuaishouVideoResponse

router = APIRouter(prefix="/kuaishou/videos", tags=["快手 Kuaishou"])


def _parse_feed(feed: dict) -> dict:
    photo = feed.get("photo") or {}
    author = feed.get("author") or {}
    return {
        "photo_id": photo.get("id", ""),
        "caption": photo.get("caption", ""),
        "timestamp": photo.get("timestamp", 0),
        "user_name": author.get("name", ""),
        "user_id": author.get("id", ""),
        "view_count": photo.get("viewCount", 0),
        "like_count": photo.get("likeCount", 0),
        "comment_count": photo.get("commentCount", 0),
        "cover_url": photo.get("coverUrl", ""),
    }


def _parse_video(photo: dict, author: dict) -> dict:
    return {
        "photo_id": photo.get("id", ""),
        "caption": photo.get("caption", ""),
        "timestamp": photo.get("timestamp", 0),
        "user_name": author.get("name", ""),
        "user_id": author.get("id", ""),
        "view_count": photo.get("viewCount", 0),
        "like_count": photo.get("likeCount", 0),
        "comment_count": photo.get("commentCount", 0),
        "cover_url": photo.get("coverUrl", ""),
    }


def _parse_comment(c: dict) -> dict:
    return {
        "comment_id": c.get("commentId", ""),
        "content": c.get("content", ""),
        "user_name": c.get("authorName", ""),
        "user_id": c.get("authorId", ""),
        "like_count": c.get("likedCount", 0),
        "timestamp": c.get("timestamp", 0),
        "sub_comment_count": c.get("subCommentCount", 0),
    }


@router.get("/search", response_model=list[KuaishouVideoResponse])
async def search_videos(
    keyword: str = Query(..., description="搜索关键词"),
    pcursor: str = Query("", description="翻页游标，首次传空字符串"),
    client: KuaishouClient = Depends(get_kuaishou_client),
):
    data = await client.search_videos(keyword, pcursor=pcursor)
    feeds = data.get("visionSearchPhoto", {}).get("feeds") or []
    return [KuaishouVideoResponse(**_parse_feed(f)) for f in feeds]


@router.get("/{photo_id}", response_model=KuaishouVideoResponse)
async def get_video(
    photo_id: str,
    client: KuaishouClient = Depends(get_kuaishou_client),
):
    data = await client.get_video_detail(photo_id)
    detail = data.get("visionVideoDetail", {})
    photo = detail.get("photo") or {}
    author = detail.get("author") or {}
    return KuaishouVideoResponse(**_parse_video(photo, author))


@router.get("/{photo_id}/comments", response_model=KuaishouCommentPageResponse)
async def get_video_comments(
    photo_id: str,
    pcursor: str = Query("", description="翻页游标"),
    client: KuaishouClient = Depends(get_kuaishou_client),
):
    data = await client.get_video_comments(photo_id, pcursor=pcursor)
    comments = [KuaishouCommentResponse(**_parse_comment(c)) for c in (data.get("rootCommentsV2") or [])]
    next_pcursor = data.get("pcursorV2", "")
    return KuaishouCommentPageResponse(
        comments=comments,
        pcursor=next_pcursor,
        has_more=next_pcursor not in ("", "no_more"),
    )
