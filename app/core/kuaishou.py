import json
from pathlib import Path
from typing import Any

import httpx
from fake_useragent import UserAgent
from fastapi import Request

from app.core.account_pool import PooledClient, PlatformAccountPool
from app.core.config import settings

KUAISHOU_BASE_URL = "https://www.kuaishou.com"

_DEFAULT_HEADERS = {
    "Referer": "https://www.kuaishou.com",
    "Origin": "https://www.kuaishou.com",
    "Accept": "application/json",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Content-Type": "application/json",
}

_GQL_SEARCH = """
fragment photoContent on PhotoEntity {
  __typename
  id
  duration
  caption
  likeCount
  viewCount
  commentCount
  coverUrl
  timestamp
}
fragment feedContent on Feed {
  type
  author {
    id
    name
    headerUrl
    __typename
  }
  photo {
    ...photoContent
    __typename
  }
  canAddComment
  __typename
}
query visionSearchPhoto($keyword: String, $pcursor: String, $searchSessionId: String, $page: String) {
  visionSearchPhoto(keyword: $keyword, pcursor: $pcursor, searchSessionId: $searchSessionId, page: $page) {
    result
    feeds {
      ...feedContent
      __typename
    }
    searchSessionId
    pcursor
    __typename
  }
}
"""

_GQL_VIDEO_DETAIL = """
query visionVideoDetail($photoId: String, $page: String) {
  visionVideoDetail(photoId: $photoId, page: $page) {
    status
    author {
      id
      name
      headerUrl
      __typename
    }
    photo {
      id
      duration
      caption
      likeCount
      viewCount
      commentCount
      coverUrl
      timestamp
      __typename
    }
    __typename
  }
}
"""

_GQL_PROFILE = """
query visionProfile($userId: String) {
  visionProfile(userId: $userId) {
    result
    userProfile {
      ownerCount {
        fan
        photo
        follow
        __typename
      }
      profile {
        gender
        user_name
        user_id
        headurl
        user_text
        __typename
      }
      __typename
    }
    __typename
  }
}
"""

_GQL_PROFILE_PHOTOS = """
fragment photoContent on PhotoEntity {
  __typename
  id
  duration
  caption
  likeCount
  viewCount
  commentCount
  coverUrl
  timestamp
}
fragment feedContent on Feed {
  type
  author {
    id
    name
    headerUrl
    __typename
  }
  photo {
    ...photoContent
    __typename
  }
  __typename
}
query visionProfilePhotoList($pcursor: String, $userId: String, $page: String) {
  visionProfilePhotoList(pcursor: $pcursor, userId: $userId, page: $page) {
    result
    feeds {
      ...feedContent
      __typename
    }
    pcursor
    __typename
  }
}
"""


class KuaishouClient(PooledClient):
    PLATFORM = "kuaishou"

    def __init__(self, pool: PlatformAccountPool) -> None:
        super().__init__(pool)
        self.REFRESH_EVERY = settings.REFRESH_EVERY
        self._client: httpx.AsyncClient | None = None
        self._ua = UserAgent()

    async def init(self) -> None:
        cookies_dir = Path(settings.COOKIES_DIR) / "kuaishou"
        await self._load_accounts(cookies_dir)
        await self._try_refresh()

    async def _refresh(self) -> None:
        cookies_dir = Path(settings.COOKIES_DIR) / "kuaishou"
        await self._load_accounts(cookies_dir)
        account = await self._select_account()
        self._username = account["username"]
        cookies = json.loads(account["cookies"])
        headers = {**_DEFAULT_HEADERS, "User-Agent": self._ua.random}
        if self._client:
            await self._client.aclose()
        self._client = httpx.AsyncClient(
            base_url=KUAISHOU_BASE_URL,
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

    async def _post_graphql(self, operation: str, variables: dict, query: str) -> Any:
        if self._client is None:
            raise RuntimeError("No kuaishou accounts configured — add cookie files to cookies/kuaishou/")
        payload = {"operationName": operation, "variables": variables, "query": query}
        try:
            resp = await self._client.post("/graphql", content=json.dumps(payload, ensure_ascii=False))
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                await self._on_auth_error(str(e))
            raise
        await self._after_request()
        body = resp.json()
        if body.get("errors"):
            raise httpx.HTTPStatusError(
                f"Kuaishou GraphQL error: {body['errors']}",
                request=resp.request,
                response=resp,
            )
        return body.get("data", {})

    async def _post_rest(self, path: str, data: dict) -> Any:
        if self._client is None:
            raise RuntimeError("No kuaishou accounts configured — add cookie files to cookies/kuaishou/")
        try:
            resp = await self._client.post(path, content=json.dumps(data, ensure_ascii=False))
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                await self._on_auth_error(str(e))
            raise
        await self._after_request()
        return resp.json()

    async def search_videos(self, keyword: str, pcursor: str = "") -> dict:
        return await self._post_graphql(
            "visionSearchPhoto",
            {"keyword": keyword, "pcursor": pcursor, "page": "search"},
            _GQL_SEARCH,
        )

    async def get_video_detail(self, photo_id: str) -> dict:
        return await self._post_graphql(
            "visionVideoDetail",
            {"photoId": photo_id, "page": "search"},
            _GQL_VIDEO_DETAIL,
        )

    async def get_video_comments(self, photo_id: str, pcursor: str = "") -> dict:
        return await self._post_rest(
            "/rest/v/photo/comment/list",
            {"photoId": photo_id, "pcursor": pcursor},
        )

    async def get_user_profile(self, user_id: str) -> dict:
        return await self._post_graphql(
            "visionProfile",
            {"userId": user_id},
            _GQL_PROFILE,
        )

    async def get_user_videos(self, user_id: str, pcursor: str = "") -> dict:
        return await self._post_graphql(
            "visionProfilePhotoList",
            {"userId": user_id, "pcursor": pcursor, "page": "profile"},
            _GQL_PROFILE_PHOTOS,
        )


def get_kuaishou_client(request: Request) -> KuaishouClient:
    return request.app.state.kuaishou_client
