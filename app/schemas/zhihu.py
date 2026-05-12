from __future__ import annotations

from pydantic import BaseModel


class ZhihuSearchItem(BaseModel):
    type: str = ""
    id: str = ""
    title: str = ""
    url: str = ""
    author_name: str = ""
    author_url_token: str = ""
    excerpt: str = ""
    created_time: int = 0
    voteup_count: int = 0
    comment_count: int = 0


class ZhihuSearchResponse(BaseModel):
    items: list[ZhihuSearchItem]
    is_end: bool = False
    next_offset: int = 0


class ZhihuCommentResponse(BaseModel):
    id: str
    content: str = ""
    author_name: str = ""
    author_url_token: str = ""
    like_count: int = 0
    created_time: int = 0
    child_comment_count: int = 0


class ZhihuCommentPageResponse(BaseModel):
    comments: list[ZhihuCommentResponse]
    is_end: bool = False
    next_offset: int = 0


class ZhihuAnswerResponse(BaseModel):
    id: str
    question_title: str = ""
    question_id: int = 0
    excerpt: str = ""
    author_name: str = ""
    author_url_token: str = ""
    voteup_count: int = 0
    comment_count: int = 0
    created_time: int = 0


class ZhihuUserAnswersResponse(BaseModel):
    answers: list[ZhihuAnswerResponse]
    is_end: bool = False
    next_offset: int = 0
    totals: int = 0


class ZhihuArticleResponse(BaseModel):
    id: str
    title: str = ""
    excerpt: str = ""
    author_name: str = ""
    voteup_count: int = 0
    comment_count: int = 0
    created: int = 0
    url: str = ""


class ZhihuUserArticlesResponse(BaseModel):
    articles: list[ZhihuArticleResponse]
    is_end: bool = False
    next_offset: int = 0
