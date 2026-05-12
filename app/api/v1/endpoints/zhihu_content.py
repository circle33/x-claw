from fastapi import APIRouter, Depends, Query

from app.core.zhihu import ZhihuClient, get_zhihu_client
from app.schemas.zhihu import ZhihuCommentPageResponse, ZhihuCommentResponse, ZhihuSearchItem, ZhihuSearchResponse

router = APIRouter(prefix="/zhihu", tags=["知乎 Zhihu"])


def _parse_search_item(item: dict) -> dict | None:
    obj = item.get("object") or {}
    t = obj.get("type", "")
    if t not in ("answer", "article", "question"):
        return None
    question = obj.get("question") or {}
    author = obj.get("author") or {}
    return {
        "type": t,
        "id": str(obj.get("id", "")),
        "title": obj.get("title", "") or question.get("title", ""),
        "url": obj.get("url", ""),
        "author_name": author.get("name", ""),
        "author_url_token": author.get("url_token", ""),
        "excerpt": obj.get("excerpt", ""),
        "created_time": obj.get("created_time", obj.get("created", 0)),
        "voteup_count": obj.get("voteup_count", 0),
        "comment_count": obj.get("comment_count", 0),
    }


def _parse_comment(c: dict) -> dict:
    author = c.get("author") or {}
    member = author.get("member") or {}
    return {
        "id": str(c.get("id", "")),
        "content": c.get("content", ""),
        "author_name": member.get("name", ""),
        "author_url_token": member.get("url_token", ""),
        "like_count": c.get("like_count", 0),
        "created_time": c.get("created_time", 0),
        "child_comment_count": c.get("child_comment_count", 0),
    }


@router.get("/search", response_model=ZhihuSearchResponse)
async def search(
    keyword: str = Query(..., description="搜索关键词"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    client: ZhihuClient = Depends(get_zhihu_client),
):
    data = await client.search(keyword, offset=offset, limit=limit)
    paging = data.get("paging") or {}
    raw_items = data.get("data") or []
    items = []
    for item in raw_items:
        parsed = _parse_search_item(item)
        if parsed:
            items.append(ZhihuSearchItem(**parsed))
    return ZhihuSearchResponse(
        items=items,
        is_end=paging.get("is_end", True),
        next_offset=offset + len(items),
    )


@router.get("/answers/{answer_id}/comments", response_model=ZhihuCommentPageResponse)
async def get_answer_comments(
    answer_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    client: ZhihuClient = Depends(get_zhihu_client),
):
    data = await client.get_answer_comments(answer_id, offset=offset, limit=limit)
    paging = data.get("paging") or {}
    comments = [ZhihuCommentResponse(**_parse_comment(c)) for c in (data.get("data") or [])]
    return ZhihuCommentPageResponse(
        comments=comments,
        is_end=paging.get("is_end", True),
        next_offset=offset + len(comments),
    )
