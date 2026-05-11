import json
from pathlib import Path

from fastapi import Request
from twscrape import API

from app.core.config import settings


def parse_cookies(cookie_file: Path) -> str:
    """从浏览器导出的 JSON cookie 文件中提取 auth_token 和 ct0，拼接为 twscrape 所需格式。"""
    cookies: list[dict] = json.loads(cookie_file.read_text(encoding="utf-8"))
    pairs: dict[str, str] = {c["name"]: c["value"] for c in cookies}
    return f"auth_token={pairs.get('auth_token', '')}; ct0={pairs.get('ct0', '')}"


def extract_username(cookie_file: Path) -> str:
    """从文件名 @username.json 提取用户名。"""
    return cookie_file.stem.lstrip("@")


async def load_accounts(api: API) -> None:
    """扫描 cookies 目录，加载所有 cookie 文件到 twscrape 账号池。"""
    cookies_dir = Path(settings.COOKIES_DIR)
    if not cookies_dir.exists():
        return

    for cookie_file in cookies_dir.rglob("@*.json"):
        username = extract_username(cookie_file)
        cookie_str = parse_cookies(cookie_file)
        await api.pool.add_account(username, "", "", "", cookies=cookie_str)

    await api.pool.login_all()


def get_api(request: Request) -> API:
    """FastAPI 依赖注入：从 app.state 获取 twscrape API 实例。"""
    return request.app.state.twscrape_api
