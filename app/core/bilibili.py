import json
import time
import urllib.parse
from hashlib import md5
from pathlib import Path
from typing import Any

import httpx
from fake_useragent import UserAgent
from fastapi import Request

from app.core.account_pool import PooledClient, PlatformAccountPool
from app.core.config import settings

BILIBILI_BASE_URL = "https://api.bilibili.com"

_DEFAULT_HEADERS = {
    "Referer": "https://www.bilibili.com",
    "Origin": "https://www.bilibili.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

_MAP_TABLE = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52,
]


class BilibiliSign:
    def __init__(self, img_key: str, sub_key: str) -> None:
        self.img_key = img_key
        self.sub_key = sub_key

    def _get_salt(self) -> str:
        mixin = self.img_key + self.sub_key
        return "".join(mixin[i] for i in _MAP_TABLE)[:32]

    def sign(self, params: dict) -> dict:
        params = {**params, "wts": int(time.time())}
        params = dict(sorted(params.items()))
        params = {k: "".join(c for c in str(v) if c not in "!'()*") for k, v in params.items()}
        query = urllib.parse.urlencode(params)
        params["w_rid"] = md5((query + self._get_salt()).encode()).hexdigest()
        return params


class BilibiliClient(PooledClient):
    PLATFORM = "bilibili"

    def __init__(self, pool: PlatformAccountPool) -> None:
        super().__init__(pool)
        self.REFRESH_EVERY = settings.REFRESH_EVERY
        self._client: httpx.AsyncClient | None = None
        self._ua = UserAgent()
        self._img_key: str = ""
        self._sub_key: str = ""

    async def init(self) -> None:
        cookies_dir = Path(settings.COOKIES_DIR) / "bilibili"
        await self._load_accounts(cookies_dir)
        await self._try_refresh()

    async def _refresh(self) -> None:
        cookies_dir = Path(settings.COOKIES_DIR) / "bilibili"
        await self._load_accounts(cookies_dir)
        account = await self._select_account()
        self._username = account["username"]
        cookies = json.loads(account["cookies"])
        headers = {**_DEFAULT_HEADERS, "User-Agent": self._ua.random}
        if self._client:
            await self._client.aclose()
        self._client = httpx.AsyncClient(
            base_url=BILIBILI_BASE_URL,
            headers=headers,
            cookies=cookies,
            timeout=30.0,
            follow_redirects=True,
            proxy=settings.PROXY,
        )
        await self._fetch_wbi_keys()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()

    async def _fetch_wbi_keys(self) -> None:
        if self._client is None:
            return
        resp = await self._client.get("/x/web-interface/nav")
        resp.raise_for_status()
        wbi = resp.json()["data"]["wbi_img"]
        self._img_key = wbi["img_url"].rsplit("/", 1)[1].split(".")[0]
        self._sub_key = wbi["sub_url"].rsplit("/", 1)[1].split(".")[0]

    def _sign(self, params: dict) -> dict:
        return BilibiliSign(self._img_key, self._sub_key).sign(params)

    async def _get(self, url: str, params: dict | None = None, sign: bool = True) -> Any:
        if self._client is None:
            raise RuntimeError("No bilibili accounts configured — add cookie files to cookies/bilibili/")
        if sign and params:
            params = self._sign(params)
        try:
            resp = await self._client.get(url, params=params)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                await self._on_auth_error(str(e))
            raise
        await self._after_request()
        body = resp.json()
        if body.get("code") != 0:
            raise httpx.HTTPStatusError(
                f"Bilibili API error {body.get('code')}: {body.get('message')}",
                request=resp.request,
                response=resp,
            )
        return body.get("data", {})

    async def search_videos(self, keyword: str, page: int = 1, page_size: int = 20) -> dict:
        return await self._get(
            "/x/web-interface/wbi/search/type",
            {"search_type": "video", "keyword": keyword, "page": page, "page_size": page_size},
        )

    async def get_video_detail(self, bvid: str) -> dict:
        return await self._get("/x/web-interface/view/detail", {"bvid": bvid}, sign=False)

    async def get_video_comments(self, oid: int, next_page: int = 0) -> dict:
        return await self._get(
            "/x/v2/reply/wbi/main",
            {"oid": oid, "type": 1, "mode": 3, "ps": 20, "next": next_page},
        )

    async def get_user_info(self, mid: int) -> dict:
        return await self._get("/x/space/wbi/acc/info", {"mid": mid})

    async def get_user_videos(self, mid: int, pn: int = 1, ps: int = 30) -> dict:
        return await self._get(
            "/x/space/wbi/arc/search",
            {"mid": mid, "pn": pn, "ps": ps, "order": "pubdate"},
        )


def get_bilibili_client(request: Request) -> BilibiliClient:
    return request.app.state.bilibili_client
