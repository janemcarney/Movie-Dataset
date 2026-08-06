"""

Runs RTScraper over a CSV of movies (e.g. exported from the Vega movies
dataset) and writes results incrementally to an output CSV.

Designed for ~3,000 movies. Safe to interrupt (Ctrl+C) and re-run —
it skips movies already present in the output file.

INPUT CSV requirements:
- must have title and year is optional

Usage:
    python3 batch_scrape.py --input movies.csv --output rt_results.csv
    python3 batch_scrape.py --input movies.csv --output rt_results.csv --limit 50   # test run first
"""

import csv
import time
import random
import argparse
import logging
from pathlib import Path

import requests
from rt_scraper import RTScraper

logger = logging.getLogger("batch_scrape")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# --- Adjust these to match your actual input CSV's column names ---
TITLE_COLUMN = "title"
YEAR_COLUMN = "year"  # set to None if your CSV has no year column

OUTPUT_FIELDS = [
    "title", "year", "status", "rt_url", "rt_title", "imdb_id",
    "critics_score", "critics_sentiment",
    "audience_score", "audience_sentiment",
    "mpaa_rating",
]


def load_already_done(output_path: Path) -> set:
    """Returns a set of (title, year) tuples already present in the output file."""
    done = set()
    if not output_path.exists():
        return done
    with open(output_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            done.add((row["title"], row["year"]))
    return done


def append_row(output_path: Path, row: dict, write_header: bool):
    with open(output_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def scrape_one(scraper: RTScraper, title: str, year) -> dict:
    row = {
        "title": title, "year": year, "status": "",
        "rt_url": "", "rt_title": "", "imdb_id": "",
        "critics_score": "", "critics_sentiment": "",
        "audience_score": "", "audience_sentiment": "",
        "mpaa_rating": "",
    }
    try:
        url = scraper.search(title, year=int(year) if year else None)
        if not url:
            row["status"] = "not_found"
            return row

        data = scraper.scrape_movie(url)
        row.update({
            "status": "ok",
            "rt_url": data.rt_url,
            "rt_title": data.title or "",
            "imdb_id": data.imdb_id or "",
            "critics_score": data.critics_score if data.critics_score is not None else "",
            "critics_sentiment": data.critics_sentiment or "",
            "audience_score": data.audience_score if data.audience_score is not None else "",
            "audience_sentiment": data.audience_sentiment or "",
            "mpaa_rating": data.mpaa_rating or "",
        })
        return row

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else "?"
        logger.error(f"HTTP {status_code} for '{title}' ({year}) — {e}")
        row["status"] = f"error_http_{status_code}"
        return row
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for '{title}' ({year}) — {e}")
        row["status"] = "error_request"
        return row
    except Exception as e:
        logger.error(f"Unexpected error for '{title}' ({year}) — {e}")
        row["status"] = "error_unexpected"
        return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to input CSV of movies")
    parser.add_argument("--output", required=True, help="Path to output CSV (created/appended)")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N movies (for testing)")
    parser.add_argument("--delay-min", type=float, default=2.0, help="Min seconds between requests")
    parser.add_argument("--delay-max", type=float, default=3.5, help="Max seconds between requests")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    with open(input_path, newline="", encoding="utf-8") as f:
        movies = list(csv.DictReader(f))

    if args.limit:
        movies = movies[: args.limit]

    already_done = load_already_done(output_path)
    write_header = not output_path.exists()

    # Use a jittered average delay (randomized per-request inside RTScraper
    # would need a custom subclass; here we approximate by setting a
    # moderate fixed delay and adding a small extra random pause per movie).
    scraper = RTScraper(delay=args.delay_min)

    total = len(movies)
    skipped = 0
    processed = 0
    start_time = time.time()

    for i, movie in enumerate(movies, 1):
        title = movie.get(TITLE_COLUMN, "").strip()
        year = movie.get(YEAR_COLUMN, "").strip() if YEAR_COLUMN else ""

        if not title:
            continue

        if (title, year) in already_done:
            skipped += 1
            continue

        row = scrape_one(scraper, title, year)
        append_row(output_path, row, write_header)
        write_header = False
        processed += 1

        # extra jitter on top of RTScraper's built-in delay, to avoid a
        # perfectly uniform request cadence
        time.sleep(random.uniform(0, args.delay_max - args.delay_min))

        if processed % 25 == 0 or i == total:
            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            remaining = total - i
            eta_min = (remaining / rate / 60) if rate > 0 else float("inf")
            logger.info(
                f"[{i}/{total}] processed={processed} skipped={skipped} "
                f"status={row['status']} — ETA ~{eta_min:.1f} min"
            )

    logger.info(f"Done. Processed {processed}, skipped {skipped} already-done, total {total}.")


if __name__ == "__main__":
    main()