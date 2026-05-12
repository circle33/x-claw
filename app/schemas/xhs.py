from __future__ import annotations

from pydantic import BaseModel


class XhsNoteResponse(BaseModel):
    note_id: str
    title: str = ""
    desc: str = ""
    type: str = ""
    user_id: str = ""
    user_name: str = ""
    liked_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    collected_count: int = 0
    xsec_token: str = ""
    cover_url: str = ""


class XhsCommentResponse(BaseModel):
    id: str
    content: str = ""
    user_id: str = ""
    user_name: str = ""
    like_count: int = 0
    create_time: int = 0
    sub_comments: list[XhsCommentResponse] = []


XhsCommentResponse.model_rebuild()


class XhsCommentPageResponse(BaseModel):
    comments: list[XhsCommentResponse]
    has_more: bool = False
    cursor: str = ""


class XhsUserNotesResponse(BaseModel):
    user_id: str
    notes: list[XhsNoteResponse]
    has_more: bool = False
    cursor: str = ""
