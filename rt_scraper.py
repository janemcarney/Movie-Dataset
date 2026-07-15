"""

Scope:
- Tomatometer (critics) score
- Audience score
- MPAA rating

Linking across datasets:
RT does NOT expose an IMDb ID anywhere on the movie page (confirmed —
no "tt" + digits pattern present at all, even in raw HTML). The "emsId"
present in several script blocks is RT's own internal UUID, not an IMDb
ID. Use title + year matching (via search()) as your join key into
TMDb/IMDb instead. `imdb_id` is kept on RTMovieData as a best-effort
field (in case some other page includes one) but expect it to be None
most of the time.

Design notes:
- Rate-limited and cached to disk so repeated test runs don't hammer the
  live site.

Usage:
    scraper = RTScraper(delay=2.0)
    url = scraper.search("The Batman", year=2022)
    data = scraper.scrape_movie(url)
"""

from __future__ import annotations

import json
import re
import time
import logging
import hashlib
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("rt_scraper")
logging.basicConfig(level=logging.INFO)


@dataclass
class RTMovieData:
    rt_url: str
    imdb_id: Optional[str] = None  # best-effort; usually None, see module docstring
    title: Optional[str] = None  # kept only for sanity-checking the match, not for your dataset
    critics_score: Optional[int] = None
    critics_sentiment: Optional[str] = None  # "POSITIVE" / "NEGATIVE", RT's own Fresh/Rotten call
    audience_score: Optional[int] = None
    audience_sentiment: Optional[str] = None
    mpaa_rating: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class RTScraper:
    BASE_URL = "https://www.rottentomatoes.com"
    SEARCH_URL = "https://www.rottentomatoes.com/search"

    def __init__(
        self,
        delay: float = 2.0,
        timeout: int = 10,
        cache_dir: str | Path = ".rt_cache",
        user_agent: str = (
            "Mozilla/5.0 (compatible; personal-research-scraper/1.0; "
            "+contact: youremail@example.com)"
        ),
    ):
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self._last_request_time = 0.0


    # Low-level fetch with rate limiting + disk cache
    # ------------------------------------------------------------------
    def _throttle(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_request_time = time.time()

    def _cache_path(self, url: str) -> Path:
        key = hashlib.sha256(url.encode()).hexdigest()
        return self.cache_dir / f"{key}.html"

    def _get(self, url: str, use_cache: bool = True) -> str:
        cache_path = self._cache_path(url)
        if use_cache and cache_path.exists():
            logger.info(f"Cache hit: {url}")
            return cache_path.read_text(encoding="utf-8")

        self._throttle()
        logger.info(f"Fetching: {url}")
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        cache_path.write_text(resp.text, encoding="utf-8")
        return resp.text

    # search
    def search(self, title: str, year: Optional[int] = None) -> Optional[str]:
        """
        Returns the best-guess RT movie URL for a title, or None if no
        results were found at all. Matching preference, in order:
        1. Case-insensitive exact title match + year match
        2. Year match only
        3. Case-insensitive exact title match only
        4. First result (last resort)
        """
        html = self._get(f"{self.SEARCH_URL}?search={requests.utils.quote(title)}")
        soup = BeautifulSoup(html, "html.parser")

        candidates = []
        for row in soup.find_all("search-page-media-row"):
            title_link = row.find("a", attrs={"data-qa": "info-name"})
            if not title_link or not title_link.get("href"):
                continue
            candidates.append({
                "title": title_link.get_text(strip=True),
                "url": title_link["href"],
                "release_year": row.get("release-year", ""),
            })

        if not candidates:
            logger.warning(f"No search results found for '{title}'")
            return None

        title_lower = title.strip().lower()
        year_str = str(year) if year else None

        # 1. exact title + year
        if year_str:
            for c in candidates:
                if c["title"].strip().lower() == title_lower and c["release_year"] == year_str:
                    return c["url"]

        # 2. year only
        if year_str:
            for c in candidates:
                if c["release_year"] == year_str:
                    return c["url"]

        # 3. exact title only
        for c in candidates:
            if c["title"].strip().lower() == title_lower:
                return c["url"]

        # 4. fallback: first result
        logger.warning(
            f"No exact match for '{title}'"
            + (f" ({year})" if year else "")
            + f" — falling back to first result: '{candidates[0]['title']}'"
        )
        return candidates[0]["url"]

    # Scrape a single movie page

    def scrape_movie(self, rt_url: str) -> RTMovieData:
        html = self._get(rt_url)
        soup = BeautifulSoup(html, "html.parser")
        result = RTMovieData(rt_url=rt_url)

        self._parse_ld_json(soup, result)
        self._parse_media_scorecard(soup, result)

        # Best-effort IMDb ID scan across the full page (expect None — see docstring)
        match = re.search(r"tt\d{6,9}", html)
        if match:
            result.imdb_id = match.group(0)

        return result

    def _parse_ld_json(self, soup: BeautifulSoup, result: RTMovieData) -> None:
        """
        Parses the schema.org Movie JSON-LD block.
        Used for: title (sanity check), MPAA rating.
        """
        tag = soup.find("script", type="application/ld+json")
        if not tag or not tag.string:
            logger.warning(f"No JSON-LD block found for {result.rt_url}")
            return
        try:
            data = json.loads(tag.string)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON-LD for {result.rt_url}")
            return

        result.title = data.get("name")
        result.mpaa_rating = data.get("contentRating")

    def _parse_media_scorecard(self, soup: BeautifulSoup, result: RTMovieData) -> None:
        """
        Parses <script id="media-scorecard-json">.
        Used for: critics score, audience score, and their sentiment labels.
        """
        tag = soup.find("script", id="media-scorecard-json")
        if not tag or not tag.string:
            logger.warning(f"No media-scorecard-json block found for {result.rt_url}")
            return
        try:
            data = json.loads(tag.string)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse media-scorecard-json for {result.rt_url}")
            return

        critics = data.get("criticsScore", {}) or {}
        audience = data.get("audienceScore", {}) or {}

        result.critics_score = self._to_int(critics.get("score"))
        result.critics_sentiment = critics.get("sentiment")
        result.audience_score = self._to_int(audience.get("score"))
        result.audience_sentiment = audience.get("sentiment")

    # Helpers

    @staticmethod
    def _to_int(val) -> Optional[int]:
        if val is None:
            return None
        try:
            return int(re.sub(r"[^\d]", "", str(val)))
        except (ValueError, TypeError):
            return None

    # Debug utility: dump both known blocks so you can spot check them

    def debug_dump_json(self, rt_url: str, out_path: str = "rt_debug.json") -> None:
        html = self._get(rt_url)
        soup = BeautifulSoup(html, "html.parser")

        ld_tag = soup.find("script", type="application/ld+json")
        scorecard_tag = soup.find("script", id="media-scorecard-json")

        dump = {
            "ld_json": json.loads(ld_tag.string) if ld_tag and ld_tag.string else None,
            "media_scorecard_json": (
                json.loads(scorecard_tag.string) if scorecard_tag and scorecard_tag.string else None
            ),
        }
        Path(out_path).write_text(json.dumps(dump, indent=2), encoding="utf-8")
        logger.info(f"Dumped JSON to {out_path}")


if __name__ == "__main__":
    scraper = RTScraper(delay=2.0)
    url = scraper.search("The Batman", year=2022)
    if url:
        print("Found:", url)
        movie = scraper.scrape_movie(url)
        print(movie.to_dict())
    else:
        print("No match found")