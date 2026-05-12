from fastapi import APIRouter, Depends, Query

from app.core.zhihu import ZhihuClient, get_zhihu_client
from app.schemas.zhihu import (
    ZhihuAnswerResponse,
    ZhihuArticleResponse,
    ZhihuUserAnswersResponse,
    ZhihuUserArticlesResponse,
)

router = APIRouter(prefix="/zhihu/users", tags=["知乎 Zhihu"])


def _parse_answer(item: dict) -> dict:
    question = item.get("question") or {}
    author = item.get("author") or {}
    return {
        "id": str(item.get("id", "")),
        "question_title": question.get("title", ""),
        "question_id": question.get("id", 0),
        "excerpt": item.get("excerpt", ""),
        "author_name": author.get("name", ""),
        "author_url_token": author.get("url_token", ""),
        "voteup_count": item.get("voteup_count", 0),
        "comment_count": item.get("comment_count", 0),
        "created_time": item.get("created_time", 0),
    }


def _parse_article(item: dict) -> dict:
    author = item.get("author") or {}
    return {
        "id": str(item.get("id", "")),
        "title": item.get("title", ""),
        "excerpt": item.get("excerpt", ""),
        "author_name": author.get("name", ""),
        "voteup_count": item.get("voteup_count", 0),
        "comment_count": item.get("comment_count", 0),
        "created": item.get("created", 0),
        "url": item.get("url", ""),
    }


@router.get("/{url_token}/answers", response_model=ZhihuUserAnswersResponse)
async def get_user_answers(
    url_token: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    client: ZhihuClient = Depends(get_zhihu_client),
):
    data = await client.get_user_answers(url_token, offset=offset, limit=limit)
    paging = data.get("paging") or {}
    answers = [ZhihuAnswerResponse(**_parse_answer(a)) for a in (data.get("data") or [])]
    return ZhihuUserAnswersResponse(
        answers=answers,
        is_end=paging.get("is_end", True),
        next_offset=offset + len(answers),
        totals=paging.get("totals", 0),
    )


@router.get("/{url_token}/articles", response_model=ZhihuUserArticlesResponse)
async def get_user_articles(
    url_token: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    client: ZhihuClient = Depends(get_zhihu_client),
):
    data = await client.get_user_articles(url_token, offset=offset, limit=limit)
    paging = data.get("paging") or {}
    articles = [ZhihuArticleResponse(**_parse_article(a)) for a in (data.get("data") or [])]
    return ZhihuUserArticlesResponse(
        articles=articles,
        is_end=paging.get("is_end", True),
        next_offset=offset + len(articles),
    )
