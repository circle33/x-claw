from fastapi import APIRouter, Depends, Path
from twscrape import API, gather

from app.core.twscrape import get_api

router = APIRouter(prefix="/trends", tags=["Twitter / X"])


@router.get(
    "/{category}",
    summary="获取热门趋势",
    description="获取 Twitter/X 上指定分类的热门趋势话题。"
    "可选分类包括：`news`（新闻）、`sport`（体育）、`entertainment`（娱乐）等。"
    "返回该分类下的热门话题列表。",
)
async def get_trends(
    category: str = Path(..., description="趋势分类，例如 news、sport、entertainment"),
    api: API = Depends(get_api),
):
    trends = await gather(api.trends(category))
    return {"category": category, "trends": trends}
