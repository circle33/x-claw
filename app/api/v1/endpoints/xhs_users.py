from fastapi import APIRouter, Depends, Query

from app.core.xhs import XhsClient, get_xhs_client
from app.schemas.xhs import XhsNoteResponse, XhsUserNotesResponse

router = APIRouter(prefix="/xhs/users", tags=["小红书 XHS"])


def _parse_note(item: dict) -> dict:
    cover = item.get("cover") or {}
    interact = item.get("interact_info") or {}
    user = item.get("user") or {}

    def _count(val) -> int:
        if isinstance(val, int):
            return val
        try:
            return int(str(val).replace("万", "0000").replace("+", ""))
        except (ValueError, TypeError):
            return 0

    return {
        "note_id": item.get("note_id", ""),
        "title": item.get("title", ""),
        "desc": item.get("desc", ""),
        "type": item.get("type", ""),
        "user_id": user.get("user_id", ""),
        "user_name": user.get("nickname", ""),
        "liked_count": _count(interact.get("liked_count", 0)),
        "comment_count": _count(interact.get("comment_count", 0)),
        "share_count": _count(interact.get("share_count", 0)),
        "collected_count": _count(interact.get("collected_count", 0)),
        "xsec_token": item.get("xsec_token", ""),
        "cover_url": cover.get("url", cover.get("info_list", [{}])[0].get("url", "") if cover.get("info_list") else ""),
    }


@router.get("/{user_id}/notes", response_model=XhsUserNotesResponse)
async def get_user_notes(
    user_id: str,
    cursor: str = Query("", description="翻页游标"),
    client: XhsClient = Depends(get_xhs_client),
):
    data = await client.get_user_notes(user_id, cursor=cursor)
    notes = [XhsNoteResponse(**_parse_note(n)) for n in (data.get("notes") or [])]
    return XhsUserNotesResponse(
        user_id=user_id,
        notes=notes,
        has_more=data.get("has_more", False),
        cursor=data.get("cursor", ""),
    )
