from fastapi import APIRouter, Depends, Query

from app.core.xhs import XhsClient, get_xhs_client
from app.schemas.xhs import XhsCommentPageResponse, XhsCommentResponse, XhsNoteResponse

router = APIRouter(prefix="/xhs/notes", tags=["小红书 XHS"])


def _parse_note(item: dict) -> dict:
    # Skip non-note items (e.g. hot_query recommendations)
    note_card = item.get("note_card")
    if not note_card:
        return {}
    cover = note_card.get("cover") or {}
    interact = note_card.get("interact_info") or {}
    user = note_card.get("user") or {}
    return {
        "note_id": note_card.get("note_id", item.get("id", "")),
        "title": note_card.get("display_title", ""),
        "desc": note_card.get("desc", ""),
        "type": note_card.get("type", ""),
        "user_id": user.get("user_id", ""),
        "user_name": user.get("nickname", user.get("nick_name", "")),
        "liked_count": _parse_count(interact.get("liked_count", "0")),
        "comment_count": _parse_count(interact.get("comment_count", "0")),
        "share_count": _parse_count(interact.get("shared_count", "0")),
        "collected_count": _parse_count(interact.get("collected_count", "0")),
        "xsec_token": item.get("xsec_token", note_card.get("xsec_token", "")),
        "cover_url": cover.get("url_default", cover.get("url_pre", "")),
    }


def _parse_count(val) -> int:
    if isinstance(val, int):
        return val
    try:
        s = str(val).replace("万", "0000").replace("+", "")
        return int(s)
    except (ValueError, TypeError):
        return 0


def _parse_comment(c: dict) -> dict:
    user = c.get("user_info") or {}
    return {
        "id": c.get("id", ""),
        "content": c.get("content", ""),
        "user_id": user.get("user_id", ""),
        "user_name": user.get("nickname", ""),
        "like_count": c.get("like_count", 0),
        "create_time": c.get("create_time", 0),
        "sub_comments": [_parse_comment(r) for r in (c.get("sub_comments") or [])],
    }


@router.get("/search", response_model=list[XhsNoteResponse])
async def search_notes(
    keyword: str = Query(..., description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    sort: str = Query("general", description="排序：general/time_descending/popularity_descending"),
    note_type: int = Query(0, description="笔记类型：0=全部, 1=视频, 2=图文"),
    client: XhsClient = Depends(get_xhs_client),
):
    data = await client.search_notes(keyword, page=page, page_size=page_size, sort=sort, note_type=note_type)
    items = data.get("items") or []
    parsed = [_parse_note(item) for item in items]
    return [XhsNoteResponse(**p) for p in parsed if p]


@router.get("/{note_id}/comments", response_model=XhsCommentPageResponse)
async def get_note_comments(
    note_id: str,
    xsec_token: str = Query(..., description="从搜索结果获取的 xsec_token"),
    cursor: str = Query("", description="翻页游标"),
    client: XhsClient = Depends(get_xhs_client),
):
    data = await client.get_note_comments(note_id, xsec_token=xsec_token, cursor=cursor)
    comments = [XhsCommentResponse(**_parse_comment(c)) for c in (data.get("comments") or [])]
    return XhsCommentPageResponse(
        comments=comments,
        has_more=data.get("has_more", False),
        cursor=data.get("cursor", ""),
    )
