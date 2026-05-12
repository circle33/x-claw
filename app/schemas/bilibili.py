from __future__ import annotations

from pydantic import BaseModel


class BilibiliVideoResponse(BaseModel):
    bvid: str
    aid: int
    title: str
    author: str
    mid: int
    pic: str
    description: str = ""
    play: int = 0
    danmaku: int = 0
    reply: int = 0
    favorite: int = 0
    coin: int = 0
    share: int = 0
    like: int = 0
    pubdate: int
    duration: str = ""
    tag: str = ""


class BilibiliVideoDetailResponse(BaseModel):
    bvid: str
    aid: int
    title: str
    desc: str = ""
    pic: str
    owner_name: str
    owner_mid: int
    view: int = 0
    danmaku: int = 0
    reply: int = 0
    favorite: int = 0
    coin: int = 0
    share: int = 0
    like: int = 0
    pubdate: int
    duration: int = 0
    tname: str = ""
    tags: list[str] = []


class BilibiliCommentResponse(BaseModel):
    rpid: int
    oid: int
    mid: int
    uname: str
    content: str
    like: int = 0
    rcount: int = 0
    ctime: int
    replies: list[BilibiliCommentResponse] = []


BilibiliCommentResponse.model_rebuild()


class BilibiliCommentPageResponse(BaseModel):
    comments: list[BilibiliCommentResponse]
    is_end: bool
    next_cursor: int


class BilibiliUserResponse(BaseModel):
    mid: int
    name: str
    sex: str = ""
    face: str = ""
    sign: str = ""
    level: int = 0
    following: int = 0
    follower: int = 0
    video_count: int = 0


class BilibiliUserVideosResponse(BaseModel):
    mid: int
    total: int
    videos: list[BilibiliVideoResponse]
