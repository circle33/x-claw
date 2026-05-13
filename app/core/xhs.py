import asyncio
import json
import logging
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fake_useragent import UserAgent
from fastapi import Request

from app.core.account_pool import PooledClient, PlatformAccountPool
from app.core.config import settings

_log = logging.getLogger(__name__)


class XhsClient(PooledClient):
    PLATFORM = "xhs"

    def __init__(self, pool: PlatformAccountPool) -> None:
        super().__init__(pool)
        self.REFRESH_EVERY = settings.REFRESH_EVERY
        self._ua = UserAgent()
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    async def init(self) -> None:
        cookies_dir = Path(settings.COOKIES_DIR) / "xhs"
        await self._load_accounts(cookies_dir)
        await self._init_playwright()
        await self._try_refresh()

    async def _init_playwright(self) -> None:
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)

    async def _refresh(self) -> None:
        cookies_dir = Path(settings.COOKIES_DIR) / "xhs"
        await self._load_accounts(cookies_dir)
        account = await self._select_account()
        self._username = account["username"]
        raw_cookies = json.loads(account["cookies"])
        ua = self._ua.chrome

        if self._context:
            await self._context.close()

        pw_cookies = [
            {"name": k, "value": v, "domain": ".xiaohongshu.com", "path": "/"}
            for k, v in raw_cookies.items()
            if k and v
        ]
        ctx_kwargs = {
            "user_agent": ua,
            "viewport": {"width": 1920, "height": 1080},
            "locale": "zh-CN",
        }
        if settings.PROXY:
            ctx_kwargs["proxy"] = {"server": settings.PROXY}
        self._context = await self._browser.new_context(**ctx_kwargs)
        if pw_cookies:
            try:
                await self._context.add_cookies(pw_cookies)
            except Exception as e:
                _log.warning("XHS: failed to add some cookies: %s", e)

        self._page = await self._context.new_page()

        # Prime the XHS security context by navigating to a search page. The
        # frontend JS (as.xiaohongshu.com) runs fingerprinting and signing
        # scripts. Then persist fresh cookies from the browser session.
        try:
            await self._page.goto(
                "https://www.xiaohongshu.com/search_result"
                "?keyword=x&source=web_search_result_notes",
                wait_until="domcontentloaded",
                timeout=30000,
            )
        except Exception as e:
            _log.warning("XHS: page initialization issue: %s", e)
        # Give the page time to load and set cookies
        await asyncio.sleep(5)
        await self._save_cookies_to_pool()

    async def _save_cookies_to_pool(self) -> None:
        if self._context is None or not self._username:
            return
        cookies = await self._context.cookies(["https://www.xiaohongshu.com"])
        cookie_dict = {c["name"]: c["value"] for c in cookies}
        if cookie_dict:
            await self._pool.upsert(self.PLATFORM, self._username, cookie_dict)
            _log.info("XHS: persisted %d cookies for account %s", len(cookie_dict), self._username)

    async def close(self) -> None:
        if self._playwright:
            await self._playwright.stop()

    async def _navigate_and_capture(self, url: str, api_path: str) -> dict | None:
        """Navigate to *url* and intercept the first matching API response.

        The XHS frontend JS handles all anti-bot signing internally. We
        navigate the shared page to trigger a full frontend init, then
        capture the XHR response containing the data we need.
        """
        response_data: dict | None = None

        async def _capture(resp):
            nonlocal response_data
            if api_path not in resp.url:
                return
            if response_data is not None:
                return  # already captured
            try:
                body = await resp.json()
                if resp.status == 200 and body.get("data", {}).get("items"):
                    response_data = body["data"]
            except Exception:
                pass

        self._page.on("response", _capture)
        try:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            _log.warning("XHS: navigation issue for %s: %s", url[:80], e)

        # Wait for the API response to come through
        for _ in range(15):
            await asyncio.sleep(1)
            if response_data is not None:
                break
        self._page.remove_listener("response", _capture)

        # Persist cookies the browser may have refreshed during API calls
        if response_data is not None:
            await self._save_cookies_to_pool()

        return response_data

    async def search_notes(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
        sort: str = "general",
        note_type: int = 0,
    ) -> dict:
        if self._page is None:
            raise RuntimeError(
                "No xhs accounts configured — add cookie files to cookies/xhs/"
            )
        search_url = (
            f"https://www.xiaohongshu.com/search_result"
            f"?keyword={quote(keyword)}&source=web_search_result_notes"
        )
        data = await self._navigate_and_capture(
            search_url, "/api/sns/web/v1/search/notes"
        )
        await self._after_request()
        return data or {"has_more": False, "items": []}

    async def get_note_comments(self, note_id: str, xsec_token: str, cursor: str = "") -> dict:
        if self._page is None:
            raise RuntimeError(
                "No xhs accounts configured — add cookie files to cookies/xhs/"
            )
        url = (
            f"https://www.xiaohongshu.com/explore/{note_id}"
            f"?xsec_token={quote(xsec_token)}&xsec_source=pc_search"
        )
        data = await self._navigate_and_capture(
            url, "/api/sns/web/v2/comment/page"
        )
        await self._after_request()
        return data or {"has_more": False, "comments": [], "cursor": ""}

    async def get_user_notes(self, user_id: str, cursor: str = "") -> dict:
        if self._page is None:
            raise RuntimeError(
                "No xhs accounts configured — add cookie files to cookies/xhs/"
            )
        url = f"https://www.xiaohongshu.com/user/profile/{user_id}"
        data = await self._navigate_and_capture(
            url, "/api/sns/web/v1/user_posted"
        )
        await self._after_request()
        return data or {"has_more": False, "items": []}


def get_xhs_client(request: Request) -> XhsClient:
    return request.app.state.xhs_client
