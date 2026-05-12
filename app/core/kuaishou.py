import json
from pathlib import Path
from typing import Any

import httpx
from fake_useragent import UserAgent
from fastapi import Request

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


def _load_cookies(cookies_dir: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for f in cookies_dir.glob("*.json"):
        for c in json.loads(f.read_text(encoding="utf-8")):
            result[c["name"]] = c["value"]
    return result


class KuaishouClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._ua = UserAgent()

    async def init(self) -> None:
        cookies_dir = Path(settings.COOKIES_DIR) / "kuaishou"
        cookies = _load_cookies(cookies_dir) if cookies_dir.exists() else {}
        headers = {**_DEFAULT_HEADERS, "User-Agent": self._ua.random}
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
        assert self._client is not None
        payload = {"operationName": operation, "variables": variables, "query": query}
        resp = await self._client.post("/graphql", content=json.dumps(payload, ensure_ascii=False))
        resp.raise_for_status()
        body = resp.json()
        if body.get("errors"):
            raise httpx.HTTPStatusError(
                f"Kuaishou GraphQL error: {body['errors']}",
                request=resp.request,
                response=resp,
            )
        return body.get("data", {})

    async def _post_rest(self, path: str, data: dict) -> Any:
        assert self._client is not None
        resp = await self._client.post(path, content=json.dumps(data, ensure_ascii=False))
        resp.raise_for_status()
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
