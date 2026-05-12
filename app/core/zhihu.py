import json
from pathlib import Path
from typing import Any

import execjs
import httpx
from fake_useragent import UserAgent
from fastapi import Request

from app.core.config import settings

ZHIHU_BASE_URL = "https://www.zhihu.com"

_DEFAULT_HEADERS = {
    "Referer": "https://www.zhihu.com",
    "Origin": "https://www.zhihu.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "x-api-version": "3.0.91",
    "x-app-za": "OS=Web",
}

_JS_PATH = Path(__file__).parent.parent.parent / "libs" / "zhihu.js"
_sign_obj = execjs.compile(_JS_PATH.read_text(encoding="utf-8"))


def _load_cookies(cookies_dir: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for f in cookies_dir.glob("*.json"):
        for c in json.loads(f.read_text(encoding="utf-8")):
            result[c["name"]] = c["value"]
    return result


def _cookies_to_str(cookies: dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


class ZhihuClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._ua = UserAgent()
        self._cookie_str: str = ""

    async def init(self) -> None:
        cookies_dir = Path(settings.COOKIES_DIR) / "zhihu"
        cookies = _load_cookies(cookies_dir) if cookies_dir.exists() else {}
        self._cookie_str = _cookies_to_str(cookies)
        ua = self._ua.random
        headers = {**_DEFAULT_HEADERS, "User-Agent": ua}
        self._client = httpx.AsyncClient(
            base_url=ZHIHU_BASE_URL,
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

    def _sign_headers(self, url: str) -> dict:
        result = _sign_obj.call("get_sign", url, self._cookie_str)
        if isinstance(result, str):
            result = json.loads(result)
        return result

    async def _get(self, path: str, params: dict | None = None) -> Any:
        assert self._client is not None
        from urllib.parse import urlencode
        full_url = path
        if params:
            full_url = f"{path}?{urlencode(params)}"
        sign_headers = self._sign_headers(full_url)
        resp = await self._client.get(path, params=params, headers=sign_headers)
        resp.raise_for_status()
        return resp.json()

    async def search(self, keyword: str, offset: int = 0, limit: int = 20) -> dict:
        return await self._get(
            "/api/v4/search_v3",
            {"q": keyword, "offset": offset, "limit": limit, "sort": "default", "vertical": "general"},
        )

    async def get_answer_comments(self, answer_id: str, offset: int = 0, limit: int = 20) -> dict:
        return await self._get(
            f"/api/v4/comment_v5/answers/{answer_id}/root_comment",
            {"order": "score", "offset": offset, "limit": limit},
        )

    async def get_user_answers(self, url_token: str, offset: int = 0, limit: int = 20) -> dict:
        return await self._get(
            f"/api/v4/members/{url_token}/answers",
            {"include": "data[*].voteup_count,comment_count,created_time", "offset": offset, "limit": limit, "order_by": "votenum"},
        )

    async def get_user_articles(self, url_token: str, offset: int = 0, limit: int = 20) -> dict:
        return await self._get(
            f"/api/v4/members/{url_token}/articles",
            {"include": "data[*].voteup_count,comment_count,created", "offset": offset, "limit": limit, "order_by": "votenum"},
        )


def get_zhihu_client(request: Request) -> ZhihuClient:
    return request.app.state.zhihu_client
