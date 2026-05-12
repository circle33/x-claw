import json
from pathlib import Path
from typing import Any

import execjs
import httpx
from fake_useragent import UserAgent
from fastapi import Request

from app.core.config import settings

DOUYIN_BASE_URL = "https://www.douyin.com"

_DEFAULT_HEADERS = {
    "Referer": "https://www.douyin.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

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
_sign_obj = execjs.compile(_JS_PATH.read_text(encoding="utf-8-sig"))


def _load_cookies(cookies_dir: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for f in cookies_dir.glob("*.json"):
        for c in json.loads(f.read_text(encoding="utf-8")):
            result[c["name"]] = c["value"]
    return result


class DouyinClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._ua = UserAgent()

    async def init(self) -> None:
        cookies_dir = Path(settings.COOKIES_DIR) / "douyin"
        cookies = _load_cookies(cookies_dir) if cookies_dir.exists() else {}
        ua = self._ua.chrome
        headers = {**_DEFAULT_HEADERS, "User-Agent": ua}
        self._ua_str = ua
        self._client = httpx.AsyncClient(
            base_url=DOUYIN_BASE_URL,
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

    def _a_bogus(self, path: str, params_str: str) -> str:
        fn = "sign_reply" if "/reply" in path else "sign_datail"
        return _sign_obj.call(fn, params_str, self._ua_str)

    async def _get(self, path: str, params: dict) -> Any:
        assert self._client is not None
        merged = {**_COMMON_PARAMS, **params}
        from urllib.parse import urlencode
        params_str = urlencode(merged)
        merged["a_bogus"] = self._a_bogus(path, params_str)
        resp = await self._client.get(path, params=merged)
        resp.raise_for_status()
        return resp.json()

    async def search_videos(self, keyword: str, offset: int = 0, count: int = 10) -> dict:
        return await self._get(
            "/aweme/v1/web/general/search/single/",
            {"search_channel": "aweme_general", "keyword": keyword, "offset": offset, "count": count, "search_id": ""},
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
