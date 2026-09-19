"""Ingest, sandbox, and corpus tests. No network calls."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.corpus.store import (
    CorpusStore,
    Incident,
    classify_kind,
    cohort_incidents,
    cohort_summary,
    extract_brand,
    find_similar,
    looks_like_backlash,
)
from app.ingest.sandbox import SandboxViolation, check_url, extract_body
from app.ingest.sources import ApifySource, RSSSource

# ── sandbox: SSRF and scheme guards ──────────────────────────────────


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8000/admin",
        "http://127.0.0.1/secrets",
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata
        "http://192.168.1.1/router",
        "http://[::1]/local",
        "https://metadata.google.internal/computeMetadata/v1/",
        "file:///etc/passwd",
        "ftp://example.com/x",
    ],
)
def test_sandbox_blocks_dangerous_urls(url):
    """Without these guards a redirect could turn the fetcher into an SSRF probe."""
    with pytest.raises(SandboxViolation):
        check_url(url)


def test_sandbox_allows_public_https():
    check_url("https://www.bbc.co.uk/news/article")


def test_body_extraction_drops_boilerplate():
    html = """
    <html><body>
    <script>tracking()</script>
    <nav><p>Home</p></nav>
    <p>Short.</p>
    <p>This is a substantial paragraph of article text that comfortably exceeds
    the eighty character minimum and should therefore be retained by the
    extractor as real content.</p>
    <footer><p>Cookie notice</p></footer>
    </body></html>
    """
    body = extract_body(html)
    assert "substantial paragraph" in body
    assert "tracking()" not in body
    assert "Short." not in body


# ── backlash filter ──────────────────────────────────────────────────


def test_filter_catches_real_backlash_headlines():
    """These are real headlines the filter must not miss."""
    for title in [
        "Converse Apologizes After Roiling Social Media With Ads That Evoke a Lynching",
        "Pepsi pulls Kendall Jenner advert after widespread criticism",
        "H&M apologises for hoodie image branded offensive",
        "Boycott calls extend to Jennie over Adidas Israel campaign",
    ]:
        ok, conf = looks_like_backlash(title)
        assert ok, f"missed real backlash: {title}"
        assert conf >= 0.4


def test_filter_rejects_ordinary_trade_news():
    """Over-inclusion is the failure that matters: a corpus of press releases
    would make the comparison panels confidently wrong."""
    for title in [
        "PepsiCo launches first-ever brand portfolio campaign",
        "Virgin Media O2 marketing boss departs after leadership shake-up",
        "No CMOs on top board of any FTSE 100 company, study finds",
        "UK creator revenue to surpass £1bn for the first time, data shows",
        "Canon rebuilt its B2B marketing function",
    ]:
        ok, _ = looks_like_backlash(title)
        assert not ok, f"false positive on trade news: {title}"


def test_backlash_verb_in_headline_is_sufficient():
    """Requiring a campaign keyword too rejected the Converse story, whose
    object was 'Ads' — the story is in the verb."""
    ok, _ = looks_like_backlash("Brand Apologizes After Roiling Social Media")
    assert ok


# ── classification and brand extraction ──────────────────────────────


def test_classify_kind_routes_by_topic():
    kind, conf = classify_kind("Brand pulls beef advert after Hindu groups protest")
    assert kind == "cultural_religious"
    assert conf > 0

    kind, _ = classify_kind("Advert criticised for greenwashing carbon claims")
    assert kind == "greenwashing"


def test_classify_unknown_is_unclassified():
    kind, conf = classify_kind("A completely unrelated sentence about nothing")
    assert kind == "unclassified"
    assert conf == 0.0


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Converse Apologizes After Roiling Social Media", "Converse"),
        ("Ralph Lauren Branded Zionist Trash Over Moment", "Ralph Lauren"),
        ("Pepsi pulls Kendall Jenner advert", "Pepsi"),
        ("H&M apologises for hoodie image", "H&M"),
        ("Why Was Kriti Sanon Rakhi Ad Pulled Down?", None),  # question word
        ("Factbox - Companies face backlash", None),  # wire marker
        ("Boycott calls extend to Jennie", None),  # not a brand
    ],
)
def test_brand_extraction(title, expected):
    assert extract_brand(title) == expected


# ── store ────────────────────────────────────────────────────────────


def _inc(iid: str, title: str, kind: str = "unclassified", conf: float = 0.5) -> Incident:
    return Incident(
        id=iid,
        title=title,
        url=f"https://example.com/{iid}",
        source="test",
        published="2026-09-01T00:00:00+00:00",
        kind=kind,
        summary=title,
        label_confidence=conf,
    )


def test_store_roundtrip_and_dedup():
    with tempfile.TemporaryDirectory() as d:
        store = CorpusStore(Path(d) / "inc.jsonl")
        assert store.add([_inc("a", "One"), _inc("b", "Two")]) == 2
        # Same URLs again must not duplicate.
        assert store.add([_inc("a", "One"), _inc("c", "Three")]) == 1
        assert len(store.load()) == 3


def test_store_survives_corrupt_line():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "inc.jsonl"
        store = CorpusStore(path)
        store.add([_inc("a", "Good")])
        with path.open("a") as fh:
            fh.write("{not json\n")
        store._cache = None
        assert len(store.load()) == 1  # bad line skipped, good one kept


def test_reliability_flag():
    assert not _inc("a", "x", conf=0.5).is_reliable
    assert _inc("b", "x", conf=0.8).is_reliable
    cur = _inc("c", "x", conf=0.1)
    cur.label_source = "curated"
    assert cur.is_reliable  # human-labelled is trusted regardless of score


# ── cohorting ────────────────────────────────────────────────────────


def test_cohorting_groups_like_failures():
    incidents = [
        _inc("a", "Brand pulls beef advert after religious protest", "cultural_religious"),
        _inc("b", "Brand pulls beef campaign after religious anger", "cultural_religious"),
        _inc("c", "Airline criticised for greenwashing carbon claims", "greenwashing"),
    ]
    cohort_incidents(incidents)
    assert incidents[0].cohort_id == incidents[1].cohort_id
    assert incidents[2].cohort_id != incidents[0].cohort_id


def test_cohort_summary_reports_reliability():
    incidents = [
        _inc("a", "Beef advert pulled after protest", "cultural_religious", conf=0.9),
        _inc("b", "Beef campaign pulled after protest", "cultural_religious", conf=0.2),
    ]
    cohort_incidents(incidents)
    summary = cohort_summary(incidents)
    assert summary
    # A cohort built from weak labels must declare that, not present as fact.
    assert 0.0 <= summary[0]["reliability"] <= 1.0


# ── similarity ───────────────────────────────────────────────────────


def test_similar_surfaces_axis_matched_incidents():
    """Copy activating dietary_practice should surface cultural incidents even
    when the vocabulary does not overlap."""
    incidents = [
        _inc(
            "a", "Snack brand withdraws campaign after religious objections", "cultural_religious"
        ),
        _inc("b", "Airline advert banned over carbon claims", "greenwashing"),
    ]
    matches = find_similar(
        incidents, "our new beef bar", activated_axes={"dietary_practice": 0.9}, limit=5
    )
    assert matches
    assert matches[0]["kind"] == "cultural_religious"


def test_similar_flags_unreliable_matches():
    incidents = [_inc("a", "Brand pulls advert after protest", "cultural_religious", conf=0.3)]
    matches = find_similar(incidents, "brand pulls advert protest", limit=3)
    assert matches[0]["caveat"] is not None
    assert "not a measured result" in matches[0]["caveat"]


def test_similar_on_empty_corpus_is_safe():
    assert find_similar([], "any copy at all") == []


# ── apify: disabled without a token ──────────────────────────────────


async def test_apify_disabled_without_token():
    """The system must work fully with no Apify token configured."""
    src = ApifySource(token="")
    assert not src.enabled
    assert await src.fetch() == []


def test_rss_uses_verified_feeds():
    """Feeds that 403 or return non-XML must not be in the defaults."""
    feeds = RSSSource().feeds
    assert feeds
    for broken in ("adage.com/rss.xml", "campaignlive.co.uk/rss"):
        assert not any(broken in u for u in feeds.values()), f"{broken} is known-blocked"
