from pydantic import BaseModel


class RedditUserResponse(BaseModel):
    id: str
    username: str
    displayname: str | None = None
    description: str | None = None
    link_karma: int = 0
    comment_karma: int = 0
    total_karma: int = 0
    created_utc: float | None = None
    is_verified: bool = False
    has_verified_email: bool = False
    is_gold: bool = False
