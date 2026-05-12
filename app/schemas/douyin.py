from __future__ import annotations

from pydantic import BaseModel


class DouyinVideoResponse(BaseModel):
    aweme_id: str
    desc: str = ""
    author_name: str = ""
    sec_uid: str = ""
    digg_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    collect_count: int = 0
    play_count: int = 0
    create_time: int = 0
    cover_url: str = ""


class DouyinVideoDetailResponse(DouyinVideoResponse):
    video_url: str = ""


class DouyinCommentResponse(BaseModel):
    cid: str
    text: str = ""
    user_name: str = ""
    uid: str = ""
    digg_count: int = 0
    create_time: int = 0
    reply_comment_total: int = 0


class DouyinCommentPageResponse(BaseModel):
    comments: list[DouyinCommentResponse]
    has_more: bool = False
    cursor: int = 0


class DouyinUserResponse(BaseModel):
    uid: str
    sec_uid: str = ""
    nickname: str = ""
    signature: str = ""
    follower_count: int = 0
    following_count: int = 0
    aweme_count: int = 0
    avatar_url: str = ""


class DouyinUserVideosResponse(BaseModel):
    sec_uid: str
    videos: list[DouyinVideoResponse]
    has_more: bool = False
    max_cursor: int = 0
