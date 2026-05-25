from __future__ import annotations

import asyncio
import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings
from app.logging import get_logger

log = get_logger(__name__)


class RobotsDisallowed(Exception):
    pass


class RequestManager:
    def __init__(self) -> None:
        s = get_settings()
        self._rps = max(s.crawl_rate_limit_rps, 0.01)
        self._respect_robots = s.crawl_respect_robots
        self._max_retries = s.crawl_max_retries
        self._headers = {"User-Agent": s.crawl_user_agent}
        client_kwargs: dict = {
            "timeout": s.crawl_timeout,
            "headers": self._headers,
            "follow_redirects": True,
            "verify": s.crawl_verify_ssl,
        }
        if s.crawl_proxy_url:
            client_kwargs["proxy"] = s.crawl_proxy_url
        self._client = httpx.AsyncClient(**client_kwargs)
        self._host_lock: dict[str, asyncio.Lock] = {}
        self._last_request: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser | None] = {}

    async def __aenter__(self) -> RequestManager:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    def _lock_for(self, host: str) -> asyncio.Lock:
        if host not in self._host_lock:
            self._host_lock[host] = asyncio.Lock()
        return self._host_lock[host]

    async def _respect_rate(self, host: str) -> None:
        min_interval = 1.0 / self._rps
        async with self._lock_for(host):
            last = self._last_request.get(host, 0.0)
            wait = min_interval - (time.monotonic() - last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request[host] = time.monotonic()

    async def _check_robots(self, url: str) -> None:
        if not self._respect_robots:
            return
        parts = urlsplit(url)
        host = parts.netloc
        if host not in self._robots:
            self._robots[host] = await self._load_robots(parts.scheme, host)
        rp = self._robots[host]
        if rp is not None and not rp.can_fetch(self._headers["User-Agent"], url):
            raise RobotsDisallowed(url)

    async def _load_robots(self, scheme: str, host: str) -> RobotFileParser | None:
        robots_url = f"{scheme}://{host}/robots.txt"
        try:
            resp = await self._client.get(robots_url)
            rp = RobotFileParser()
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
            else:
                rp.parse([])
            return rp
        except httpx.HTTPError:
            log.warning("robots.fetch_failed", host=host)
            return None

    async def get(self, url: str) -> httpx.Response:
        await self._check_robots(url)
        host = urlsplit(url).netloc
        await self._respect_rate(host)

        @retry(
            retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            reraise=True,
        )
        async def _do() -> httpx.Response:
            resp = await self._client.get(url)
            if resp.status_code == 429 or resp.status_code >= 500:
                resp.raise_for_status()
            return resp

        return await _do()

    async def get_json(self, url: str) -> dict:
        resp = await self.get(url)
        resp.raise_for_status()
        return resp.json()
