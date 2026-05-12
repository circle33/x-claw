from __future__ import annotations

from pydantic import BaseModel


class KuaishouVideoResponse(BaseModel):
    photo_id: str
    caption: str = ""
    timestamp: int = 0
    user_name: str = ""
    user_id: str = ""
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    cover_url: str = ""


class KuaishouCommentResponse(BaseModel):
    comment_id: str
    content: str = ""
    user_name: str = ""
    user_id: str = ""
    like_count: int = 0
    timestamp: int = 0
    sub_comment_count: int = 0


class KuaishouCommentPageResponse(BaseModel):
    comments: list[KuaishouCommentResponse]
    pcursor: str = ""
    has_more: bool = False


class KuaishouUserResponse(BaseModel):
    user_id: str
    name: str = ""
    description: str = ""
    fans_count: int = 0
    follows_count: int = 0
    photo_count: int = 0
    avatar_url: str = ""


class KuaishouUserVideosResponse(BaseModel):
    user_id: str
    videos: list[KuaishouVideoResponse]
    pcursor: str = ""
