import json
import logging
from pathlib import Path
from typing import Any

from fake_useragent import UserAgent
from fastapi import Request
from playwright.async_api import BrowserContext, async_playwright

from app.core.account_pool import PooledClient, PlatformAccountPool
from app.core.config import settings

ZHIHU_BASE_URL = "https://www.zhihu.com"

_DEFAULT_HEADERS = {
    "Referer": "https://www.zhihu.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "x-api-version": "3.0.91",
    "x-app-za": "OS=Web",
}

_log = logging.getLogger(__name__)


class ZhihuClient(PooledClient):
    PLATFORM = "zhihu"

    def __init__(self, pool: PlatformAccountPool) -> None:
        super().__init__(pool)
        self.REFRESH_EVERY = settings.REFRESH_EVERY
        self._ua = UserAgent()
        self._playwright = None
        self._browser = None
        self._context: BrowserContext | None = None

    async def init(self) -> None:
        cookies_dir = Path(settings.COOKIES_DIR) / "zhihu"
        await self._load_accounts(cookies_dir)

        self._playwright = await async_playwright().start()
        proxy = {"server": settings.PROXY} if settings.PROXY else None
        self._browser = await self._playwright.chromium.launch(headless=True, proxy=proxy)
        self._context = await self._browser.new_context(
            user_agent=self._ua.random,
            extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
        )
        await self._try_refresh()

    async def _refresh(self) -> None:
        cookies_dir = Path(settings.COOKIES_DIR) / "zhihu"
        await self._load_accounts(cookies_dir)
        account = await self._select_account()
        self._username = account["username"]
        cookies = json.loads(account["cookies"])
        cookie_list = [
            {"name": k, "value": v, "domain": ".zhihu.com", "path": "/"}
            for k, v in cookies.items()
        ]
        assert self._context is not None
        await self._context.clear_cookies()
        await self._context.add_cookies(cookie_list)
        page = await self._context.new_page()
        try:
            await page.goto(
                "https://www.zhihu.com/search?type=content&q=python",
                wait_until="domcontentloaded",
                timeout=25000,
            )
        except Exception as e:
            _log.warning("Zhihu: warmup goto failed: %s", e)
        finally:
            await page.close()
        await self._save_cookies_to_pool()

    async def _save_cookies_to_pool(self) -> None:
        if self._context is None or not self._username:
            return
        cookies = await self._context.cookies(["https://www.zhihu.com"])
        cookie_dict = {c["name"]: c["value"] for c in cookies}
        if cookie_dict:
            await self._pool.upsert(self.PLATFORM, self._username, cookie_dict)
            _log.info("Zhihu: persisted %d cookies for account %s", len(cookie_dict), self._username)

    async def close(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def _get(self, path: str, params: dict | None = None) -> Any:
        if self._context is None:
            raise RuntimeError("No zhihu accounts configured — add cookie files to cookies/zhihu/")
        url = ZHIHU_BASE_URL + path
        resp = await self._context.request.get(url, params=params, headers=_DEFAULT_HEADERS)
        if not resp.ok:
            if resp.status in (401, 403):
                await self._on_auth_error(f"Zhihu API {resp.status}: {url}")
            raise Exception(f"Zhihu API {resp.status}: {url}")
        await self._after_request()
        return await resp.json()

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
