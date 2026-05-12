import json
from pathlib import Path
from typing import Any

import httpx
from fake_useragent import UserAgent
from fastapi import Request

from app.core.config import settings

WEIBO_BASE_URL = "https://m.weibo.cn"

_DEFAULT_HEADERS = {
    "Referer": "https://m.weibo.cn",
    "Origin": "https://m.weibo.cn",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "MWeibo-Pwa": "1",
}


def _load_cookies(cookies_dir: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for f in cookies_dir.glob("*.json"):
        for c in json.loads(f.read_text(encoding="utf-8")):
            result[c["name"]] = c["value"]
    return result


class WeiboClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._ua = UserAgent()

    async def init(self) -> None:
        cookies_dir = Path(settings.COOKIES_DIR) / "weibo"
        cookies = _load_cookies(cookies_dir) if cookies_dir.exists() else {}
        headers = {**_DEFAULT_HEADERS, "User-Agent": self._ua.random}
        self._client = httpx.AsyncClient(
            base_url=WEIBO_BASE_URL,
            headers=headers,
            cookies=cookies,
            timeout=30.0,
            follow_redirects=True,
            trust_env=False,
            proxy=settings.PROXY,
        )

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()

    async def _get(self, path: str, params: dict | None = None) -> Any:
        assert self._client is not None
        resp = await self._client.get(path, params=params)
        resp.raise_for_status()
        body = resp.json()
        if body.get("ok") != 1:
            raise httpx.HTTPStatusError(
                f"Weibo API error: {body.get('msg', body)}",
                request=resp.request,
                response=resp,
            )
        return body.get("data", {})

    async def search_posts(self, keyword: str, page: int = 1, search_type: int = 1) -> dict:
        return await self._get(
            "/api/container/getIndex",
            {"containerid": f"100103type={search_type}&q={keyword}", "page_type": "searchall", "page": page},
        )

    async def get_post_comments(self, mid: str, max_id: int = 0) -> dict:
        return await self._get(
            "/comments/hotflow",
            {"id": mid, "mid": mid, "max_id_type": 0, "max_id": max_id},
        )

    async def get_user_info(self, user_id: str) -> dict:
        return await self._get(
            "/api/container/getIndex",
            {"containerid": f"100505{user_id}"},
        )

    async def get_user_posts(self, container_id: str, since_id: str = "") -> dict:
        params: dict = {"containerid": container_id}
        if since_id:
            params["since_id"] = since_id
        return await self._get("/api/container/getIndex", params)


def get_weibo_client(request: Request) -> WeiboClient:
    return request.app.state.weibo_client
