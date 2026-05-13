import json
import logging
from pathlib import Path

import httpx
from fake_useragent import UserAgent
from fastapi import Request

from app.core.account_pool import PooledClient, PlatformAccountPool
from app.core.config import settings

REDDIT_BASE_URL = "https://www.reddit.com"
_log = logging.getLogger(__name__)

_DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,zh-TW;q=0.8,zh-HK;q=0.7,en-US;q=0.6,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "TE": "trailers",
}


class RedditClient(PooledClient):
    PLATFORM = "reddit"

    def __init__(self, pool: PlatformAccountPool) -> None:
        super().__init__(pool)
        self._client: httpx.AsyncClient | None = None
        self._ua = UserAgent()

    async def init(self) -> None:
        cookies_dir = Path(settings.COOKIES_DIR) / "reddit"
        await self._load_accounts(cookies_dir)
        await self._try_refresh()
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=REDDIT_BASE_URL,
                headers={**_DEFAULT_HEADERS, "User-Agent": self._ua.random},
                timeout=30.0,
                follow_redirects=True,
                proxy=settings.PROXY,
            )

    async def _refresh(self) -> None:
        cookies_dir = Path(settings.COOKIES_DIR) / "reddit"
        await self._load_accounts(cookies_dir)
        accounts = await self._pool.get_active(self.PLATFORM)
        cookies = json.loads(accounts[0]["cookies"]) if accounts else {}
        if accounts:
            self._username = accounts[0]["username"]
        headers = {**_DEFAULT_HEADERS, "User-Agent": self._ua.random}
        if self._client:
            await self._client.aclose()
        self._client = httpx.AsyncClient(
            base_url=REDDIT_BASE_URL,
            headers=headers,
            cookies=cookies,
            timeout=30.0,
            follow_redirects=True,
            proxy=settings.PROXY,
        )
        await self._save_cookies_to_pool()

    async def _save_cookies_to_pool(self) -> None:
        if self._client is None or not self._username:
            return
        cookie_dict = dict(self._client.cookies)
        if cookie_dict:
            await self._pool.upsert(self.PLATFORM, self._username, cookie_dict)
            _log.info("Reddit: persisted %d cookies for account %s", len(cookie_dict), self._username)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()

    async def _get(self, url: str, params: dict | None = None) -> httpx.Response:
        assert self._client is not None
        return await self._client.get(url, params=params)

    # --- 公开方法 ---

    async def search(
        self, query: str, limit: int = 20, sort: str = "relevance"
    ) -> list[dict]:
        resp = await self._get(
            "/search.json",
            params={"q": query, "limit": limit, "sort": sort},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["data"]["children"]

    async def get_post(self, subreddit: str, post_id: str) -> list[dict]:
        resp = await self._get(
            f"/r/{subreddit}/comments/{post_id}.json",
        )
        resp.raise_for_status()
        return resp.json()

    async def get_post_comments(
        self, subreddit: str, post_id: str, limit: int = 20
    ) -> list[dict]:
        resp = await self._get(
            f"/r/{subreddit}/comments/{post_id}.json",
            params={"limit": limit, "depth": 5},
        )
        resp.raise_for_status()
        data = resp.json()
        if len(data) >= 2:
            return data[1]["data"]["children"]
        return []

    async def get_user(self, username: str) -> dict | None:
        resp = await self._get(f"/user/{username}/about.json")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()["data"]

    async def get_user_posts(
        self, username: str, limit: int = 20
    ) -> list[dict]:
        resp = await self._get(
            f"/user/{username}/submitted.json",
            params={"limit": limit},
        )
        resp.raise_for_status()
        return resp.json()["data"]["children"]

    async def get_user_comments(
        self, username: str, limit: int = 20
    ) -> list[dict]:
        resp = await self._get(
            f"/user/{username}/comments.json",
            params={"limit": limit},
        )
        resp.raise_for_status()
        return resp.json()["data"]["children"]

    async def get_subreddit(
        self, subreddit: str, limit: int = 20
    ) -> list[dict]:
        resp = await self._get(
            f"/r/{subreddit}.json", params={"limit": limit}
        )
        resp.raise_for_status()
        return resp.json()["data"]["children"]

    async def get_popular(self, limit: int = 20) -> list[dict]:
        resp = await self._get("/r/popular.json", params={"limit": limit})
        resp.raise_for_status()
        return resp.json()["data"]["children"]


def get_reddit_client(request: Request) -> RedditClient:
    return request.app.state.reddit_client
