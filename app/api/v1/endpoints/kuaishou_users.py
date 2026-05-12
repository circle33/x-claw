from fastapi import APIRouter, Depends, Query

from app.core.kuaishou import KuaishouClient, get_kuaishou_client
from app.schemas.kuaishou import KuaishouUserResponse, KuaishouUserVideosResponse, KuaishouVideoResponse

router = APIRouter(prefix="/kuaishou/users", tags=["快手 Kuaishou"])


def _parse_user(profile_data: dict) -> dict:
    user_profile = profile_data.get("visionProfile", {}).get("userProfile", {})
    profile = user_profile.get("profile", {})
    counts = user_profile.get("ownerCount", {})
    return {
        "user_id": profile.get("user_id", ""),
        "name": profile.get("user_name", ""),
        "description": profile.get("user_text", ""),
        "fans_count": counts.get("fan", 0),
        "follows_count": counts.get("follow", 0),
        "photo_count": counts.get("photo", 0),
        "avatar_url": profile.get("headurl", ""),
    }


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


@router.get("/{user_id}", response_model=KuaishouUserResponse)
async def get_user(
    user_id: str,
    client: KuaishouClient = Depends(get_kuaishou_client),
):
    data = await client.get_user_profile(user_id)
    return KuaishouUserResponse(**_parse_user(data))


@router.get("/{user_id}/videos", response_model=KuaishouUserVideosResponse)
async def get_user_videos(
    user_id: str,
    pcursor: str = Query("", description="翻页游标"),
    client: KuaishouClient = Depends(get_kuaishou_client),
):
    data = await client.get_user_videos(user_id, pcursor=pcursor)
    photo_list = data.get("visionProfilePhotoList", {})
    feeds = photo_list.get("feeds") or []
    next_pcursor = photo_list.get("pcursor", "")
    return KuaishouUserVideosResponse(
        user_id=user_id,
        videos=[KuaishouVideoResponse(**_parse_feed(f)) for f in feeds],
        pcursor=next_pcursor,
    )
