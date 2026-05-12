from __future__ import annotations

from pydantic import BaseModel


class WeiboUserResponse(BaseModel):
    id: str
    screen_name: str
    description: str = ""
    followers_count: int = 0
    follow_count: int = 0
    statuses_count: int = 0
    profile_image_url: str = ""


class WeiboPostResponse(BaseModel):
    mid: str
    bid: str = ""
    text: str = ""
    user_name: str = ""
    user_id: str = ""
    reposts_count: int = 0
    comments_count: int = 0
    attitudes_count: int = 0
    created_at: str = ""


class WeiboCommentResponse(BaseModel):
    id: str
    text: str = ""
    user_name: str = ""
    user_id: str = ""
    like_count: int = 0
    created_at: str = ""
    replies: list[WeiboCommentResponse] = []


WeiboCommentResponse.model_rebuild()


class WeiboCommentPageResponse(BaseModel):
    comments: list[WeiboCommentResponse]
    max_id: int = 0
    max_id_type: int = 0
