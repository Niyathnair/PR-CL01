"""Live news sources.

Three drivers behind one interface:

- ``GDELTSource``  — free, global, 15-minute refresh. No auth. The bulk source.
- ``RSSSource``    — free, curated marketing/adland trade press. No auth.
- ``ApifySource``  — optional, paid. Social reaction volume via Apify actors,
  which handle the scraping infrastructure so no personal account is involved.

**On trade press versus social.** Backlash gets *documented* in AdAge, Marketing
Week, Campaign and Adweek far more reliably than it surfaces in a raw social
firehose. The quote-tweet dunk is the symptom; the trade write-up is the event
with an outcome attached. For corpus building, RSS over those outlets is better
signal than social, not a consolation prize.

Every source returns ``[]`` on failure rather than raising. A dead feed must
cost accuracy, never a run.
"""

from __future__ import annotations

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

# Trade press writes up campaign failures with outcomes attached. General news
# covers the biggest incidents only.
# Verified reachable and returning parseable RSS as of 2026-09-19. Feeds rot;
# `GET /v1/ingest/feeds/health` re-checks them at runtime rather than assuming.
# AdAge (403) and CampaignLive (403) block automated clients even with a UA, and
# TheDrum returns non-XML — all excluded rather than left to fail silently.
DEFAULT_FEEDS: dict[str, str] = {
    "adweek": "https://www.adweek.com/feed/",
    "marketingweek": "https://www.marketingweek.com/feed/",
    "marketingdive": "https://www.marketingdive.com/feeds/news/",
    "guardian_media": "https://www.theguardian.com/media/rss",
    "bbc_business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "nyt_business": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    "cnbc_business": (
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147"
    ),
}

# Terms that co-occur with campaign backlash reporting. Used to filter feeds and
# to query GDELT.
BACKLASH_TERMS = (
    "advert backlash",
    "campaign backlash",
    "ad pulled",
    "advert withdrawn",
    "campaign withdrawn",
    "apologises advert",
    "apologizes ad",
    "offensive advert",
    "brand boycott",
    "tone deaf campaign",
    "advertising controversy",
)


@dataclass
class RawArticle:
    """A news item before it becomes context or a corpus entry."""

    title: str
    url: str
    source: str
    published: str
    summary: str = ""
    body: str = ""
    provider: str = "unknown"

    def as_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published": self.published,
            "summary": self.summary,
            "body": self.body[:5000],
            "provider": self.provider,
        }


class NewsSource(Protocol):
    name: str

    async def fetch(
        self, *, query: str | None = None, window_days: int = 7
    ) -> list[RawArticle]: ...


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"&[a-z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class GDELTSource:
    """GDELT 2.0 Doc API — free, no key, global coverage, 15-minute refresh.

    Build this first: it is free and genuinely good. Its weakness is that it
    returns headlines and metadata, not article bodies, which is why the
    article fetcher exists.
    """

    name = "gdelt"
    ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"

    def __init__(self, timeout: float = 20.0, max_records: int = 60) -> None:
        self.timeout = timeout
        self.max_records = max_records

    async def fetch(self, *, query: str | None = None, window_days: int = 7) -> list[RawArticle]:
        q = query or " OR ".join(f'"{t}"' for t in BACKLASH_TERMS[:6])
        params = {
            "query": f"({q}) sourcelang:english",
            "mode": "ArtList",
            "maxrecords": str(self.max_records),
            "timespan": f"{max(1, window_days)}d",
            "format": "json",
            "sort": "hybridrel",
        }

        # GDELT's public endpoint throttles aggressively and answers 429 with no
        # Retry-After. Back off and retry rather than losing the cycle's bulk
        # source to a transient limit.
        payload: dict[str, Any] = {}
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(
                        self.ENDPOINT,
                        params=params,
                        headers={"User-Agent": "crowdLens/0.1 (+research)"},
                    )
                if resp.status_code == 429:
                    wait = 5 * (attempt + 1)
                    logger.info("GDELT rate-limited, retrying in %ds", wait)
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                # GDELT occasionally returns HTML on error with a 200.
                if "application/json" not in resp.headers.get("content-type", ""):
                    logger.warning("GDELT returned non-JSON; treating as empty")
                    return []
                payload = resp.json()
                break
            except Exception as exc:  # noqa: BLE001 - a dead feed must not break a run
                logger.warning("GDELT fetch failed (attempt %d): %s", attempt + 1, exc)
                if attempt == 2:
                    return []
                await asyncio.sleep(3)

        if not payload:
            return []

        out: list[RawArticle] = []
        for a in payload.get("articles", []):
            seendate = a.get("seendate", "")
            try:
                published = (
                    datetime.strptime(seendate, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).isoformat()
                )
            except ValueError:
                published = datetime.now(UTC).isoformat()

            out.append(
                RawArticle(
                    title=a.get("title", "").strip(),
                    url=a.get("url", ""),
                    source=a.get("domain", "unknown"),
                    published=published,
                    provider=self.name,
                )
            )
        logger.info("GDELT returned %d articles", len(out))
        return out


class RSSSource:
    """Curated trade-press feeds. Free, no auth, and the best backlash signal."""

    name = "rss"

    def __init__(self, feeds: dict[str, str] | None = None, timeout: float = 15.0) -> None:
        self.feeds = feeds or DEFAULT_FEEDS
        self.timeout = timeout

    async def fetch(self, *, query: str | None = None, window_days: int = 7) -> list[RawArticle]:
        cutoff = datetime.now(UTC) - timedelta(days=max(1, window_days))
        out: list[RawArticle] = []

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": "crowdLens/0.1 (+research)"},
        ) as client:
            for name, url in self.feeds.items():
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    root = ET.fromstring(resp.content)
                except Exception as exc:  # noqa: BLE001 - one bad feed is not fatal
                    logger.warning("RSS feed %s failed: %s", name, exc)
                    continue

                # Handles both RSS <item> and Atom <entry>.
                items = root.findall(".//item") or root.findall(
                    ".//{http://www.w3.org/2005/Atom}entry"
                )
                for item in items:
                    art = self._parse_item(item, name, cutoff)
                    if art:
                        out.append(art)

        logger.info("RSS returned %d articles from %d feeds", len(out), len(self.feeds))
        return out

    def _parse_item(self, item: ET.Element, feed_name: str, cutoff: datetime) -> RawArticle | None:
        def find(*tags: str) -> str:
            for tag in tags:
                el = item.find(tag)
                if el is not None:
                    if el.text:
                        return el.text.strip()
                    href = el.get("href")
                    if href:
                        return href.strip()
            return ""

        title = find("title", "{http://www.w3.org/2005/Atom}title")
        link = find("link", "{http://www.w3.org/2005/Atom}link")
        if not title or not link:
            return None

        raw_date = find(
            "pubDate",
            "{http://purl.org/dc/elements/1.1/}date",
            "{http://www.w3.org/2005/Atom}published",
            "{http://www.w3.org/2005/Atom}updated",
        )
        published = self._parse_date(raw_date)
        if published and published < cutoff:
            return None

        return RawArticle(
            title=title,
            url=link,
            source=feed_name,
            published=(published or datetime.now(UTC)).isoformat(),
            summary=_strip_html(find("description", "{http://www.w3.org/2005/Atom}summary"))[:600],
            provider=self.name,
        )

    @staticmethod
    def _parse_date(raw: str) -> datetime | None:
        if not raw:
            return None
        for fmt in (
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(raw.strip(), fmt)
                return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
            except ValueError:
                continue
        return None


class ApifySource:
    """Social reaction volume via Apify actors.

    Apify runs and maintains the scrapers, so no personal account is used and no
    session cookie lives in this repo. A customer supplies their own
    ``APIFY_TOKEN`` exactly as they would any other API key, which is what makes
    this shippable where a logged-in scraper would not be.

    Two caveats worth stating rather than burying:

    1. This shifts legal exposure, it does not remove it. Scraping public data is
       broadly defensible, but X's terms prohibit it and X has litigated against
       scrapers. Apify carries the operational risk; commercial use of the data
       still warrants a lawyer's read.
    2. Cost is usage-based (roughly $0.25-$1 per 1,000 items plus a monthly
       floor). Cheaper than X's own tier at low volume, more expensive at high.

    Disabled unless a token is configured. The system works fully without it.
    """

    name = "apify"
    BASE = "https://api.apify.com/v2"
    # Default actor: a widely used X/Twitter search scraper. Override via config
    # if you prefer a different one, or point at a Reddit/TikTok actor instead.
    DEFAULT_ACTOR = "apidojo~tweet-scraper"

    def __init__(
        self,
        token: str | None = None,
        actor: str | None = None,
        timeout: float = 120.0,
        max_items: int = 100,
    ) -> None:
        self.token = (token or "").strip()
        self.actor = actor or self.DEFAULT_ACTOR
        self.timeout = timeout
        self.max_items = max_items

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    async def fetch(self, *, query: str | None = None, window_days: int = 7) -> list[RawArticle]:
        if not self.enabled:
            logger.debug("Apify source skipped: no APIFY_TOKEN configured")
            return []

        search = query or "advert backlash OR campaign pulled OR tone deaf ad"
        payload = {
            "searchTerms": [search],
            "maxItems": self.max_items,
            "sort": "Top",
            "tweetLanguage": "en",
        }

        url = f"{self.BASE}/acts/{quote(self.actor, safe='~')}/run-sync-get-dataset-items"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, params={"token": self.token}, json=payload)
                resp.raise_for_status()
                items = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Apify fetch failed: %s", exc)
            return []

        if not isinstance(items, list):
            logger.warning("Apify returned unexpected payload shape")
            return []

        out: list[RawArticle] = []
        for it in items:
            text = (it.get("text") or it.get("full_text") or "").strip()
            if not text:
                continue
            author = (it.get("author") or {}).get("userName") or it.get("username") or "unknown"
            out.append(
                RawArticle(
                    title=text[:160],
                    url=it.get("url") or it.get("twitterUrl") or "",
                    source=f"x/{author}",
                    published=it.get("createdAt") or datetime.now(UTC).isoformat(),
                    summary=text[:600],
                    body=text,
                    provider=self.name,
                )
            )
        logger.info("Apify returned %d social items", len(out))
        return out


async def fetch_article_body(url: str, timeout: float = 20.0) -> str:
    """Fetch and crudely extract an article body.

    GDELT gives headlines, not text. Corpus entries need the body to describe
    what actually happened. This is deliberately simple: a full readability
    implementation is not worth the dependency when a paragraph heuristic gets
    most of the way.
    """
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "crowdLens/0.1 (+research)"},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
    except Exception as exc:  # noqa: BLE001
        logger.debug("Article fetch failed for %s: %s", url, exc)
        return ""

    # Strip scripts and styles before extracting paragraph text.
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html, flags=re.S | re.I)
    text = " ".join(_strip_html(p) for p in paragraphs)
    # Very short results usually mean a JS-rendered page; the browser sandbox
    # handles those.
    return text.strip()[:12000]
