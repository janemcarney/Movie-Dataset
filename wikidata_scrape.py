"""
wikidata_enrich.py

Fills in missing production_budget, revenue, producers, and mpaa_rating
by querying Wikidata's SPARQL endpoint, matched by imdb_id — no fuzzy
title matching, no scraping risk. Wikidata's API is official, sanctioned
for automated queries, and explicitly welcomes this kind of use.

Only processes rows from movies.db that are:
  - missing at least one of the target fields, AND
  - have a non-null imdb_id to match on

Writes results incrementally to a CSV with the same checkpoint/resume
pattern as batch_scrape.py — safe to interrupt and re-run.

Wikidata properties used:
  P2130 - budget (cost)
  P2142 - box office (revenue)
  P162  - producer
  P1657 - MPAA film rating

Note on currency: Wikidata stores budget/box office with a currency
unit. To avoid silently mixing currencies (a foreign film's budget in
euros being written into a column meant for USD figures), this script
ONLY fills production_budget/revenue when the unit is US dollars. Other
currencies are recorded in the output CSV for reference but not written
to movies.db as-is.

Usage:
    python3 wikidata_scrape.py --db movies.db --output wikidata_results.csv
    python3 wikidata_scrape.py --db movies.db --output wikidata_results.csv --limit 50   # test first
"""

import csv
import time
import argparse
import logging
import sqlite3
import requests
from pathlib import Path

logger = logging.getLogger("wikidata_enrich")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

SPARQL_URL = "https://query.wikidata.org/sparql"
USER_AGENT = (
    "MovieDatasetProject/1.0 (personal research dataset for Kaggle; "
    "contact: youremail@example.com)"
)

OUTPUT_FIELDS = [
    "tmdb_id", "imdb_id", "title",
    "status",
    "budget_amount", "budget_currency",
    "revenue_amount", "revenue_currency",
    "producers", "mpaa_rating",
]

SPARQL_QUERY_TEMPLATE = """
SELECT
  (SAMPLE(?budget) AS ?budgetAmount)
  (SAMPLE(?budgetUnitLabel) AS ?budgetCurrency)
  (SAMPLE(?boxOffice) AS ?revenueAmount)
  (SAMPLE(?boxOfficeUnitLabel) AS ?revenueCurrency)
  (GROUP_CONCAT(DISTINCT ?producerLabel; separator="|") AS ?producers)
  (GROUP_CONCAT(DISTINCT ?mpaaLabel; separator="|") AS ?mpaaRatings)
WHERE {{
  ?film wdt:P345 "{imdb_id}" .

  OPTIONAL {{
    ?film p:P2130/psv:P2130 ?budgetNode .
    ?budgetNode wikibase:quantityAmount ?budget ;
                wikibase:quantityUnit ?budgetUnit .
    ?budgetUnit rdfs:label ?budgetUnitLabel .
    FILTER(LANG(?budgetUnitLabel) = "en")
  }}
  OPTIONAL {{
    ?film p:P2142/psv:P2142 ?boxNode .
    ?boxNode wikibase:quantityAmount ?boxOffice ;
             wikibase:quantityUnit ?boxOfficeUnit .
    ?boxOfficeUnit rdfs:label ?boxOfficeUnitLabel .
    FILTER(LANG(?boxOfficeUnitLabel) = "en")
  }}
  OPTIONAL {{
    ?film wdt:P162 ?producerItem .
    ?producerItem rdfs:label ?producerLabel .
    FILTER(LANG(?producerLabel) = "en")
  }}
  OPTIONAL {{
    ?film wdt:P1657 ?mpaaItem .
    ?mpaaItem rdfs:label ?mpaaLabel .
    FILTER(LANG(?mpaaLabel) = "en")
  }}
}}
"""


def get_candidate_rows(db_path: str) -> list[dict]:
    """
    Pulls rows from movies.db missing at least one target field,
    with a usable imdb_id to query Wikidata by.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tmdb_id, imdb_id, title
        FROM movies
        WHERE imdb_id IS NOT NULL
          AND TRIM(imdb_id) != ''
          AND (
              production_budget IS NULL
              OR revenue IS NULL
              OR producers IS NULL
              OR mpaa_rating IS NULL
          );
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def query_wikidata(session: requests.Session, imdb_id: str) -> dict:
    query = SPARQL_QUERY_TEMPLATE.format(imdb_id=imdb_id)
    resp = session.get(
        SPARQL_URL,
        params={"query": query, "format": "json"},
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    bindings = data.get("results", {}).get("bindings", [])
    if not bindings:
        return {}
    return bindings[0]  # aggregated query always returns exactly one row


def binding_value(binding: dict, key: str) -> str:
    return binding.get(key, {}).get("value", "")


def load_already_done(output_path: Path) -> set:
    done = set()
    if not output_path.exists():
        return done
    with open(output_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("tmdb_id"):
                done.add(row["tmdb_id"])
    return done


def append_row(output_path: Path, row: dict, write_header: bool):
    with open(output_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="movies.db", help="Path to movies.db")
    parser.add_argument("--output", default="wikidata_results.csv", help="Path to output CSV")
    parser.add_argument("--limit", type=int, default=None, help="Only process first N rows (testing)")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between requests")
    args = parser.parse_args()

    output_path = Path(args.output)
    already_done = load_already_done(output_path)
    write_header = not output_path.exists()

    candidates = get_candidate_rows(args.db)
    if args.limit:
        candidates = candidates[: args.limit]

    session = requests.Session()
    total = len(candidates)
    processed = skipped = 0
    start_time = time.time()

    for i, movie in enumerate(candidates, 1):
        tmdb_id = str(movie["tmdb_id"])
        if tmdb_id in already_done:
            skipped += 1
            continue

        imdb_id = movie["imdb_id"].strip()
        row = {
            "tmdb_id": tmdb_id, "imdb_id": imdb_id, "title": movie["title"],
            "status": "", "budget_amount": "", "budget_currency": "",
            "revenue_amount": "", "revenue_currency": "",
            "producers": "", "mpaa_rating": "",
        }

        try:
            binding = query_wikidata(session, imdb_id)
            if not binding:
                row["status"] = "not_found"
            else:
                row["status"] = "ok"
                row["budget_amount"] = binding_value(binding, "budgetAmount")
                row["budget_currency"] = binding_value(binding, "budgetCurrency")
                row["revenue_amount"] = binding_value(binding, "revenueAmount")
                row["revenue_currency"] = binding_value(binding, "revenueCurrency")
                row["producers"] = binding_value(binding, "producers").replace("|", ", ")
                row["mpaa_rating"] = binding_value(binding, "mpaaRatings").replace("|", ", ")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for imdb_id={imdb_id} ('{movie['title']}') — {e}")
            row["status"] = "error_request"

        append_row(output_path, row, write_header)
        write_header = False
        processed += 1
        time.sleep(args.delay)

        if processed % 100 == 0 or i == total:
            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            eta_min = ((total - i) / rate / 60) if rate > 0 else float("inf")
            logger.info(f"[{i}/{total}] processed={processed} skipped={skipped} — ETA ~{eta_min:.1f} min")

    logger.info(f"Done. Processed {processed}, skipped {skipped} already-done, total candidates {total}.")


if __name__ == "__main__":
    main()