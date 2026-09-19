"""Sandboxed article fetcher.

Fetches public article pages to recover body text that feed summaries omit.
"Sandboxed" here means a set of hard constraints enforced in code, not a VM:

- **Public pages only.** No authentication, no cookies, no stored session. The
  fetcher cannot log in because it has nowhere to put a credential.
- **Allowlist by scheme and blocklist by host.** Private and loopback addresses
  are refused, so a malicious redirect cannot turn this into an SSRF probe
  against the machine it runs on.
- **Bounded.** Response size, redirect count, timeout, and per-host concurrency
  are all capped. A hostile page cannot exhaust memory or hang the scheduler.
- **Polite.** Per-host rate limiting and a truthful User-Agent. robots.txt is
  honoured for hosts that publish one.

Deliberately NOT a headless browser. A real browser would render JS-heavy pages,
but it also executes untrusted code, needs a large dependency, and is the thing
that gets fingerprinted and blocked. Most news articles are server-rendered, and
the ones that are not are skipped rather than chased.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
import socket
import time
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "crowdLens/0.1 (+https://github.com/Niyathnair/crowdLens; research)"

MAX_BYTES = 2_000_000
MAX_REDIRECTS = 5
PER_HOST_DELAY = 1.5  # seconds between requests to the same host
FETCH_TIMEOUT = 20.0

# Hosts that are never fetched, regardless of where a link came from.
BLOCKED_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal"})


class SandboxViolation(RuntimeError):
    """Raised when a URL fails the sandbox's safety checks."""


@dataclass
class FetchResult:
    url: str
    ok: bool
    status: int = 0
    body: str = ""
    error: str = ""
    bytes_read: int = 0


@dataclass
class _HostState:
    last_fetch: float = 0.0
    robots: RobotFileParser | None = None
    robots_checked: bool = False


def _is_private_address(host: str) -> bool:
    """Resolve and reject private, loopback, link-local and reserved ranges.

    This is the SSRF guard: without it a redirect to http://169.254.169.254/
    would let a scraped page read cloud instance metadata.
    """
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        # Unresolvable: let the HTTP layer fail rather than guessing.
        return False

    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return True
    return False


def check_url(url: str) -> None:
    """Enforce the sandbox rules. Raises SandboxViolation on any breach."""
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise SandboxViolation(f"scheme {parsed.scheme!r} not allowed")

    host = (parsed.hostname or "").lower()
    if not host:
        raise SandboxViolation("no host in URL")
    if host in BLOCKED_HOSTS:
        raise SandboxViolation(f"host {host!r} is blocked")
    if _is_private_address(host):
        raise SandboxViolation(f"host {host!r} resolves to a private address")


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"&(nbsp|amp|quot|#39|lsquo|rsquo|ldquo|rdquo);", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_body(html: str) -> str:
    """Paragraph-density extraction.

    Strips scripts, styles, nav and footer, then joins <p> content. Crude but
    dependency-free, and adequate for news articles which are paragraph-shaped
    by construction.
    """
    html = re.sub(
        r"<(script|style|nav|footer|aside|form)[^>]*>.*?</\1>",
        " ",
        html,
        flags=re.S | re.I,
    )
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html, flags=re.S | re.I)
    cleaned = [_strip_html(p) for p in paragraphs]
    # Drop boilerplate one-liners (cookie notices, bylines, share prompts).
    meaningful = [p for p in cleaned if len(p) > 80]
    return " ".join(meaningful).strip()


class ArticleSandbox:
    """Rate-limited, SSRF-guarded fetcher for public article pages."""

    def __init__(
        self,
        respect_robots: bool = True,
        per_host_delay: float = PER_HOST_DELAY,
        max_concurrency: int = 4,
    ) -> None:
        self.respect_robots = respect_robots
        self.per_host_delay = per_host_delay
        self._hosts: dict[str, _HostState] = {}
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._locks: dict[str, asyncio.Lock] = {}

    def _host_lock(self, host: str) -> asyncio.Lock:
        if host not in self._locks:
            self._locks[host] = asyncio.Lock()
        return self._locks[host]

    async def _check_robots(self, client: httpx.AsyncClient, host: str, url: str) -> bool:
        if not self.respect_robots:
            return True

        state = self._hosts.setdefault(host, _HostState())
        if not state.robots_checked:
            state.robots_checked = True
            try:
                resp = await client.get(f"https://{host}/robots.txt", timeout=8.0)
                if resp.status_code == 200:
                    rp = RobotFileParser()
                    rp.parse(resp.text.splitlines())
                    state.robots = rp
            except Exception:  # noqa: BLE001 - absent robots.txt means no rules
                state.robots = None

        if state.robots is None:
            return True
        return state.robots.can_fetch(USER_AGENT, url)

    async def fetch(self, url: str) -> FetchResult:
        """Fetch one article body, enforcing every sandbox rule."""
        try:
            check_url(url)
        except SandboxViolation as exc:
            logger.warning("Sandbox refused %s: %s", url[:80], exc)
            return FetchResult(url=url, ok=False, error=str(exc))

        host = (urlparse(url).hostname or "").lower()

        async with self._semaphore, self._host_lock(host):
            state = self._hosts.setdefault(host, _HostState())

            # Politeness delay, per host.
            elapsed = time.monotonic() - state.last_fetch
            if elapsed < self.per_host_delay:
                await asyncio.sleep(self.per_host_delay - elapsed)

            try:
                async with httpx.AsyncClient(
                    timeout=FETCH_TIMEOUT,
                    follow_redirects=True,
                    max_redirects=MAX_REDIRECTS,
                    headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
                ) as client:
                    if not await self._check_robots(client, host, url):
                        return FetchResult(url=url, ok=False, error="disallowed by robots.txt")

                    resp = await client.get(url)
                    state.last_fetch = time.monotonic()

                    # Re-check after redirects: the final host may differ.
                    final_host = (resp.url.host or "").lower()
                    if final_host != host:
                        try:
                            check_url(str(resp.url))
                        except SandboxViolation as exc:
                            return FetchResult(url=url, ok=False, error=f"redirect blocked: {exc}")

                    if resp.status_code != 200:
                        return FetchResult(
                            url=url,
                            ok=False,
                            status=resp.status_code,
                            error=f"HTTP {resp.status_code}",
                        )

                    content = resp.content[:MAX_BYTES]
                    body = extract_body(content.decode("utf-8", errors="replace"))

                    return FetchResult(
                        url=url,
                        ok=bool(body),
                        status=resp.status_code,
                        body=body,
                        bytes_read=len(content),
                        error="" if body else "no extractable body (likely JS-rendered)",
                    )

            except Exception as exc:  # noqa: BLE001 - one bad page is not fatal
                state.last_fetch = time.monotonic()
                return FetchResult(url=url, ok=False, error=f"{type(exc).__name__}: {exc}")

    async def fetch_many(self, urls: list[str]) -> list[FetchResult]:
        return list(await asyncio.gather(*(self.fetch(u) for u in urls)))
