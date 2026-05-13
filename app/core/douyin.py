import json
import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from fake_useragent import UserAgent
from fastapi import Request

from app.core.account_pool import PooledClient, PlatformAccountPool
from app.core.config import settings

_log = logging.getLogger(__name__)

DOUYIN_BASE_URL = "https://www.douyin.com"

_COMMON_PARAMS = {
    "device_platform": "webapp",
    "aid": "6383",
    "channel": "channel_pc_web",
    "pc_client_type": "1",
    "version_code": "190500",
    "version_name": "19.5.0",
    "cookie_enabled": "true",
    "screen_width": "1920",
    "screen_height": "1080",
    "browser_language": "zh-CN",
    "browser_platform": "Win32",
    "browser_name": "Chrome",
    "browser_version": "120.0.0.0",
    "browser_online": "true",
    "engine_name": "Blink",
    "os_name": "Windows",
    "os_version": "10",
    "cpu_core_num": "8",
    "device_memory": "8",
    "platform": "PC",
    "downlink": "10",
    "effective_type": "4g",
    "round_trip_time": "50",
}

_JS_PATH = Path(__file__).parent.parent.parent / "libs" / "douyin.js"


class DouyinClient(PooledClient):
    PLATFORM = "douyin"

    def __init__(self, pool: PlatformAccountPool) -> None:
        super().__init__(pool)
        self.REFRESH_EVERY = settings.REFRESH_EVERY
        self._ua = UserAgent()
        self._ua_str: str = ""
        self._playwright = None
        self._browser = None
        self._page = None
        self._context = None

    async def init(self) -> None:
        cookies_dir = Path(settings.COOKIES_DIR) / "douyin"
        await self._load_accounts(cookies_dir)
        await self._init_playwright()
        await self._try_refresh()

    async def _init_playwright(self) -> None:
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)

    async def _refresh(self) -> None:
        cookies_dir = Path(settings.COOKIES_DIR) / "douyin"
        await self._load_accounts(cookies_dir)
        account = await self._select_account()
        self._username = account["username"]
        raw_cookies = json.loads(account["cookies"])
        ua = self._ua.chrome
        self._ua_str = ua

        # Close old context if refreshing
        if self._context:
            await self._context.close()

        # Create Playwright context with stored cookies
        pw_cookies = [
            {"name": k, "value": v, "domain": ".douyin.com", "path": "/"}
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
                _log.warning("Douyin: failed to add some cookies: %s", e)

        self._page = await self._context.new_page()

        # Navigate to douyin.com to establish a real browser session.
        # This lets Douyin's anti-bot JS run and issue fresh session cookies.
        try:
            await self._page.goto(
                "https://www.douyin.com/", wait_until="domcontentloaded", timeout=30000
            )
            await self._page.wait_for_timeout(3000)
        except Exception as e:
            _log.warning("Douyin: page navigation issue: %s", e)

        # Persist fresh cookies from the browser session
        fresh_cookies_list = await self._context.cookies()
        fresh_cookies = {
            c["name"]: c["value"] for c in fresh_cookies_list if c.get("name")
        }
        if fresh_cookies:
            await self._pool.upsert(self.PLATFORM, self._username, fresh_cookies)
            _log.info(
                "Douyin: persisted %d fresh cookies from browser", len(fresh_cookies)
            )

    async def close(self) -> None:
        if self._playwright:
            await self._playwright.stop()

    async def _get(self, path: str, params: dict) -> Any:
        """Make API request through the browser's native fetch().

        This uses the real browser TLS stack and JS environment, bypassing
        Douyin's anti-bot TLS fingerprint detection that blocks httpx.
        """
        if self._page is None:
            raise RuntimeError(
                "No douyin accounts configured — add cookie files to cookies/douyin/"
            )
        merged = {**_COMMON_PARAMS, **params}
        qs = urlencode(merged)

        result = await self._page.evaluate(
            """
            async ({path, qs}) => {
                const url = 'https://www.douyin.com' + path + '?' + qs;
                try {
                    const resp = await fetch(url, {
                        credentials: 'include',
                        headers: {
                            'Referer': 'https://www.douyin.com/',
                            'Accept': 'application/json, text/plain, */*',
                        }
                    });
                    return {ok: true, data: await resp.json()};
                } catch (err) {
                    return {ok: false, error: err.message};
                }
            }
            """,
            {"path": path, "qs": qs},
        )

        if not result.get("ok"):
            raise RuntimeError(f"Douyin API request failed: {result.get('error')}")

        body = result["data"]

        # Handle auth errors
        if body.get("status_code") in (2,) or body.get("status_msg"):
            msg = body.get("status_msg", "")
            if "不合法" in msg or "token" in msg.lower():
                await self._on_auth_error(msg)

        await self._after_request()
        return body

    async def search_videos(self, keyword: str, offset: int = 0, count: int = 10) -> dict:
        return await self._get(
            "/aweme/v1/web/general/search/single/",
            {
                "search_channel": "aweme_general",
                "keyword": keyword,
                "offset": offset,
                "count": count,
                "search_id": "",
            },
        )

    async def get_video_detail(self, aweme_id: str) -> dict:
        return await self._get("/aweme/v1/web/aweme/detail/", {"aweme_id": aweme_id})

    async def get_video_comments(self, aweme_id: str, cursor: int = 0, count: int = 20) -> dict:
        return await self._get(
            "/aweme/v1/web/comment/list/",
            {"aweme_id": aweme_id, "cursor": cursor, "count": count, "item_type": 0},
        )

    async def get_user_info(self, sec_user_id: str) -> dict:
        return await self._get(
            "/aweme/v1/web/user/profile/other/",
            {"sec_user_id": sec_user_id, "publish_video_strategy_type": 2},
        )

    async def get_user_videos(self, sec_user_id: str, max_cursor: int = 0, count: int = 18) -> dict:
        return await self._get(
            "/aweme/v1/web/aweme/post/",
            {"sec_user_id": sec_user_id, "max_cursor": max_cursor, "count": count},
        )


def get_douyin_client(request: Request) -> DouyinClient:
    return request.app.state.douyin_client
