import json
from pathlib import Path
from typing import Any

import httpx
from fake_useragent import UserAgent
from fastapi import Request
from xhshow import Xhshow

from app.core.config import settings

XHS_BASE_URL = "https://edith.xiaohongshu.com"

_DEFAULT_HEADERS = {
    "Referer": "https://www.xiaohongshu.com",
    "Origin": "https://www.xiaohongshu.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def _load_cookies(cookies_dir: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for f in cookies_dir.glob("*.json"):
        for c in json.loads(f.read_text(encoding="utf-8")):
            result[c["name"]] = c["value"]
    return result


def _cookies_to_str(cookies: dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


class XhsClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._ua = UserAgent()
        self._cookie_str: str = ""

    async def init(self) -> None:
        cookies_dir = Path(settings.COOKIES_DIR) / "xhs"
        cookies = _load_cookies(cookies_dir) if cookies_dir.exists() else {}
        self._cookie_str = _cookies_to_str(cookies)
        ua = self._ua.random
        headers = {**_DEFAULT_HEADERS, "User-Agent": ua}
        self._client = httpx.AsyncClient(
            base_url=XHS_BASE_URL,
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

    def _sign_post(self, uri: str, payload: dict) -> dict:
        xhshow = Xhshow()
        return xhshow.sign_headers_post(uri=uri, cookies=self._cookie_str, payload=json.dumps(payload))

    def _sign_get(self, uri: str, params: dict) -> dict:
        xhshow = Xhshow()
        return xhshow.sign_headers_get(uri=uri, cookies=self._cookie_str, params=params)

    async def _post(self, uri: str, payload: dict) -> Any:
        assert self._client is not None
        extra_headers = self._sign_post(uri, payload)
        resp = await self._client.post(
            uri,
            content=json.dumps(payload, ensure_ascii=False),
            headers={**extra_headers, "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        body = resp.json()
        if body.get("success") is False:
            raise httpx.HTTPStatusError(
                f"XHS API error: {body.get('msg', body)}",
                request=resp.request,
                response=resp,
            )
        return body.get("data", body)

    async def _get(self, uri: str, params: dict | None = None) -> Any:
        assert self._client is not None
        extra_headers = self._sign_get(uri, params or {})
        resp = await self._client.get(uri, params=params, headers=extra_headers)
        resp.raise_for_status()
        body = resp.json()
        if body.get("success") is False:
            raise httpx.HTTPStatusError(
                f"XHS API error: {body.get('msg', body)}",
                request=resp.request,
                response=resp,
            )
        return body.get("data", body)

    async def search_notes(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
        sort: str = "general",
        note_type: int = 0,
    ) -> dict:
        uri = "/api/sns/web/v1/search/notes"
        payload = {
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "search_id": "",
            "sort": sort,
            "note_type": note_type,
            "image_formats": ["jpg", "webp", "avif"],
        }
        return await self._post(uri, payload)

    async def get_note_comments(self, note_id: str, xsec_token: str, cursor: str = "") -> dict:
        uri = "/api/sns/web/v2/comment/page"
        params: dict = {
            "note_id": note_id,
            "cursor": cursor,
            "top_comment_id": "",
            "image_formats": "jpg,webp,avif",
            "xsec_token": xsec_token,
        }
        return await self._get(uri, params)

    async def get_user_notes(self, user_id: str, cursor: str = "") -> dict:
        uri = "/api/sns/web/v1/user_posted"
        params: dict = {
            "num": 30,
            "cursor": cursor,
            "user_id": user_id,
            "image_formats": "jpg,webp,avif",
            "xsec_source": "pc_user",
            "xsec_token": "",
        }
        return await self._get(uri, params)


def get_xhs_client(request: Request) -> XhsClient:
    return request.app.state.xhs_client
