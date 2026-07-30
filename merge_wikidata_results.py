"""
merge_wikidata_results.py

Merges wikidata_results.csv into movies.db, joined by tmdb_id.

Only writes production_budget/revenue when the currency is specifically
"United States dollar" — other currencies (Reichsmark, Australian
dollar, etc.) are left out of the numeric columns to avoid silently
mixing currencies. Producers and mpaa_rating are currency-independent
and always merged in when present.

Usage:
    python3 merge_wikidata_results.py --input wikidata_results.csv --db movies.db
"""

import csv
import argparse
from movie_database import MovieDatabase

USD_LABEL = "united states dollar"


def to_int_or_none(val):
    val = (val or "").strip()
    if not val:
        return None
    try:
        return int(float(val))  # Wikidata amounts sometimes come as "160000000" or "1.6E8"-style
    except ValueError:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to wikidata_results.csv")
    parser.add_argument("--db", default="movies.db", help="Path to movies.db")
    args = parser.parse_args()

    db = MovieDatabase(args.db)
    db.create_table()

    with open(args.input, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    updated = 0
    no_match_in_db = 0
    skipped_no_tmdb_id = 0
    skipped_not_ok = 0
    non_usd_budget_skipped = 0
    non_usd_revenue_skipped = 0

    for row in rows:
        if row.get("status") != "ok":
            skipped_not_ok += 1
            continue

        tmdb_id = to_int_or_none(row.get("tmdb_id"))
        if tmdb_id is None:
            skipped_no_tmdb_id += 1
            continue

        budget = None
        if (row.get("budget_currency") or "").strip().lower() == USD_LABEL:
            budget = to_int_or_none(row.get("budget_amount"))
        elif (row.get("budget_amount") or "").strip():
            non_usd_budget_skipped += 1

        revenue = None
        if (row.get("revenue_currency") or "").strip().lower() == USD_LABEL:
            revenue = to_int_or_none(row.get("revenue_amount"))
        elif (row.get("revenue_amount") or "").strip():
            non_usd_revenue_skipped += 1

        producers = row.get("producers") or None
        mpaa_rating = row.get("mpaa_rating") or None

        rows_affected = db.update_wikidata_data(
            tmdb_id=tmdb_id,
            production_budget=budget,
            revenue=revenue,
            producers=producers,
            mpaa_rating=mpaa_rating,
        )

        if rows_affected > 0:
            updated += 1
        else:
            no_match_in_db += 1

    print("--- Summary ---")
    print(f"Updated in movies.db: {updated}")
    print(f"No matching tmdb_id in movies.db: {no_match_in_db}")
    print(f"Skipped (status != ok): {skipped_not_ok}")
    print(f"Skipped (missing tmdb_id): {skipped_no_tmdb_id}")
    print(f"Non-USD budget values not written (currency mismatch): {non_usd_budget_skipped}")
    print(f"Non-USD revenue values not written (currency mismatch): {non_usd_revenue_skipped}")
    print(f"Total rows in CSV: {len(rows)}")


if __name__ == "__main__":
    main()