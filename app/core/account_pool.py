import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

_log = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS platform_accounts (
    platform   TEXT NOT NULL,
    username   TEXT NOT NULL,
    cookies    TEXT NOT NULL DEFAULT '{}',
    active     INTEGER NOT NULL DEFAULT 1,
    stats      TEXT NOT NULL DEFAULT '{}',
    last_used  TEXT,
    error_msg  TEXT,
    PRIMARY KEY (platform, username)
)
"""


class PlatformAccountPool:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute(_SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    async def upsert(self, platform: str, username: str, cookies: dict) -> None:
        assert self._db is not None
        await self._db.execute(
            """
            INSERT INTO platform_accounts (platform, username, cookies, active, stats)
            VALUES (?, ?, ?, 1, '{"requests": 0}')
            ON CONFLICT(platform, username) DO UPDATE SET
                cookies = excluded.cookies,
                active = 1,
                error_msg = NULL
            """,
            (platform, username, json.dumps(cookies, ensure_ascii=False)),
        )
        await self._db.commit()

    async def get_active(self, platform: str) -> list[dict]:
        assert self._db is not None
        async with self._db.execute(
            """
            SELECT platform, username, cookies, active, stats, last_used, error_msg
            FROM platform_accounts
            WHERE platform = ? AND active = 1
            ORDER BY CAST(json_extract(stats, '$.requests') AS INTEGER) ASC
            """,
            (platform,),
        ) as cur:
            rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def increment(self, platform: str, username: str) -> int:
        assert self._db is not None
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            """
            UPDATE platform_accounts
            SET stats = json_set(stats, '$.requests',
                        CAST(json_extract(stats, '$.requests') AS INTEGER) + 1),
                last_used = ?
            WHERE platform = ? AND username = ?
            """,
            (now, platform, username),
        )
        await self._db.commit()
        async with self._db.execute(
            "SELECT CAST(json_extract(stats, '$.requests') AS INTEGER) FROM platform_accounts WHERE platform=? AND username=?",
            (platform, username),
        ) as cur:
            row = await cur.fetchone()
        return row[0] if row else 0

    async def reset_stats(self, platform: str, username: str) -> None:
        assert self._db is not None
        await self._db.execute(
            "UPDATE platform_accounts SET stats = '{\"requests\": 0}' WHERE platform=? AND username=?",
            (platform, username),
        )
        await self._db.commit()

    async def mark_error(self, platform: str, username: str, error: str) -> None:
        assert self._db is not None
        _log.warning("Platform %s account %s marked inactive: %s", platform, username, error)
        await self._db.execute(
            "UPDATE platform_accounts SET active=0, error_msg=? WHERE platform=? AND username=?",
            (error[:500], platform, username),
        )
        await self._db.commit()

    async def all_accounts(self) -> list[dict]:
        assert self._db is not None
        async with self._db.execute(
            "SELECT platform, username, active, stats, last_used, error_msg FROM platform_accounts ORDER BY platform, username"
        ) as cur:
            rows = await cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            stats = json.loads(d.pop("stats") or "{}")
            d["requests"] = stats.get("requests", 0)
            d["active"] = bool(d["active"])
            result.append(d)
        return result


class PooledClient:
    PLATFORM: str = ""
    REFRESH_EVERY: int = 500

    def __init__(self, pool: PlatformAccountPool) -> None:
        self._pool = pool
        self._username: str = ""

    async def _load_accounts(self, cookies_dir: Path) -> None:
        if not cookies_dir.exists():
            return
        for f in cookies_dir.glob("*.json"):
            try:
                raw = json.loads(f.read_text(encoding="utf-8"))
                cookies = {c["name"]: c["value"] for c in raw}
                await self._pool.upsert(self.PLATFORM, f.stem, cookies)
            except Exception as e:
                _log.warning("Failed to load cookie file %s: %s", f, e)

    async def _select_account(self) -> dict[str, Any]:
        accounts = await self._pool.get_active(self.PLATFORM)
        if not accounts:
            raise RuntimeError(f"No active {self.PLATFORM} accounts available")
        return accounts[0]

    async def _after_request(self) -> None:
        count = await self._pool.increment(self.PLATFORM, self._username)
        if count >= self.REFRESH_EVERY:
            _log.info("Platform %s account %s reached %d requests, refreshing", self.PLATFORM, self._username, count)
            await self._pool.reset_stats(self.PLATFORM, self._username)
            await self._refresh()

    async def _on_auth_error(self, error: str) -> None:
        await self._pool.mark_error(self.PLATFORM, self._username, error)
        try:
            await self._refresh()
        except RuntimeError:
            _log.error("Platform %s: no fallback account available after auth error", self.PLATFORM)

    async def _try_refresh(self) -> None:
        """Call _refresh() but warn instead of crash when no accounts exist."""
        try:
            await self._refresh()
        except RuntimeError as e:
            _log.warning("Platform %s: %s — add cookie files to enable this platform", self.PLATFORM, e)

    async def _refresh(self) -> None:
        raise NotImplementedError
