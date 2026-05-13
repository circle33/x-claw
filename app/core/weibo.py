import json
import logging
from pathlib import Path
from typing import Any

import httpx
from fake_useragent import UserAgent
from fastapi import Request

from app.core.account_pool import PooledClient, PlatformAccountPool
from app.core.config import settings

_log = logging.getLogger(__name__)

WEIBO_BASE_URL = "https://m.weibo.cn"

_DEFAULT_HEADERS = {
    "Referer": "https://m.weibo.cn",
    "Origin": "https://m.weibo.cn",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "MWeibo-Pwa": "1",
}


class WeiboClient(PooledClient):
    PLATFORM = "weibo"

    def __init__(self, pool: PlatformAccountPool) -> None:
        super().__init__(pool)
        self.REFRESH_EVERY = settings.REFRESH_EVERY
        self._client: httpx.AsyncClient | None = None
        self._ua = UserAgent()

    async def init(self) -> None:
        cookies_dir = Path(settings.COOKIES_DIR) / "weibo"
        await self._load_accounts(cookies_dir)
        await self._try_refresh()

    async def _refresh(self) -> None:
        cookies_dir = Path(settings.COOKIES_DIR) / "weibo"
        await self._load_accounts(cookies_dir)
        account = await self._select_account()
        self._username = account["username"]
        cookies = json.loads(account["cookies"])
        headers = {**_DEFAULT_HEADERS, "User-Agent": self._ua.random}
        if self._client:
            await self._client.aclose()
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
        if self._client is None:
            raise RuntimeError("No weibo accounts configured — add cookie files to cookies/weibo/")
        try:
            resp = await self._client.get(path, params=params)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                await self._on_auth_error(str(e))
            raise
        # Check for non-JSON response (login page, captcha, etc.)
        ctype = resp.headers.get("content-type", "")
        if "json" not in ctype:
            _log.warning("Weibo: non-JSON response (content-type=%s), session may be invalid", ctype)
            _log.debug("Weibo: body preview: %s", resp.text[:300])
            await self._on_auth_error(f"non-JSON response (content-type={ctype})")
            raise RuntimeError("Weibo session expired or login required")
        try:
            body = resp.json()
        except json.JSONDecodeError:
            _log.warning("Weibo: failed to decode JSON response")
            await self._on_auth_error("JSON decode failure")
            raise
        await self._after_request()
        if body.get("ok") != 1:
            await self._on_auth_error(f"API error: {body.get('msg', 'unknown')}")
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
