from pydantic import BaseModel


class RedditPostResponse(BaseModel):
    id: str
    title: str
    selftext: str | None = None
    subreddit: str
    author: str | None = None
    score: int = 0
    upvote_ratio: float = 0.0
    num_comments: int = 0
    created_utc: float
    url: str
    permalink: str
    link_flair_text: str | None = None
    over_18: bool = False
    thumbnail: str | None = None
    is_self: bool = True


class RedditCommentResponse(BaseModel):
    id: str
    author: str | None = None
    body: str
    score: int = 0
    created_utc: float
    permalink: str
    replies: list["RedditCommentResponse"] = []
