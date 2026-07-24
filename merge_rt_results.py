"""
merge_rt_results.py

Merges rt_results.csv (RT scrape output) into movies.db.

Joins strictly by tmdb_id — never by title — so two movies that happen
to share a title (e.g. a remake) can never get each other's data mixed
up. Rows with a missing/blank tmdb_id are skipped and reported, since
there's nothing safe to join them on.

Usage:
    python3 merge_rt_results.py --input rt_results.csv --db movies.db
"""

import csv
import argparse
import sqlite3
from movie_database import MovieDatabase


def to_int_or_none(val):
    val = (val or "").strip()
    return int(val) if val else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to rt_results.csv")
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
    skipped_duplicate_url = 0

    for row in rows:
        if row.get("status") != "ok":
            skipped_not_ok += 1
            continue

        tmdb_id = to_int_or_none(row.get("tmdb_id"))
        if tmdb_id is None:
            skipped_no_tmdb_id += 1
            print(f"  SKIPPED (no tmdb_id): '{row.get('title')}' — can't safely join this row")
            continue

        rt_url = row.get("rt_url") or None

        try:
            rows_affected = db.update_rotten_tomatoes_data(
                tmdb_id=tmdb_id,
                rotten_tomatoes_url=rt_url,
                audience_rating=to_int_or_none(row.get("audience_score")),
                critics_rating=to_int_or_none(row.get("critics_score")),
                mpaa_rating=row.get("mpaa_rating") or None,
            )

            if rows_affected > 0:
                updated += 1
            else:
                # tmdb_id from the CSV doesn't exist in movies.db at all —
                # this means the row was never inserted by the TMDb import step
                no_match_in_db += 1
                print(f"  NO DB MATCH: tmdb_id={tmdb_id} ('{row.get('title')}') not found in movies.db")

        except sqlite3.IntegrityError:
            skipped_duplicate_url += 1
            print(
                f"  SKIPPED (duplicate RT URL): tmdb_id={tmdb_id} ('{row.get('title')}') "
                f"tried to use URL already in DB: {rt_url}"
            )

    print("\n--- Summary ---")
    print(f"Updated in movies.db: {updated}")
    print(f"No matching tmdb_id in movies.db: {no_match_in_db}")
    print(f"Skipped (status != ok): {skipped_not_ok}")
    print(f"Skipped (missing tmdb_id in CSV): {skipped_no_tmdb_id}")
    print(f"Skipped (duplicate RT URL): {skipped_duplicate_url}")
    print(f"Total rows in CSV: {len(rows)}")


if __name__ == "__main__":
    main()