"""
merge_imdb_datasets_results.py

Usage:
    python3 merge_imdb_datasets_results.py --input imdb_datasets_results.csv --db movies.db
"""

import csv
import argparse
from movie_database import MovieDatabase


def to_int_or_none(val):
    val = (val or "").strip()
    return int(val) if val else None


def to_float_or_none(val):
    val = (val or "").strip()
    return float(val) if val else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to imdb_datasets_results.csv")
    parser.add_argument("--db", default="movies.db", help="Path to movies.db")
    args = parser.parse_args()

    db = MovieDatabase(args.db)
    db.create_table()

    with open(args.input, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    updated = 0
    no_match_in_db = 0
    skipped_no_tmdb_id = 0

    for row in rows:
        tmdb_id = to_int_or_none(row.get("tmdb_id"))
        if tmdb_id is None:
            skipped_no_tmdb_id += 1
            continue

        rows_affected = db.update_imdb_datasets_data(
            tmdb_id=tmdb_id,
            genre=row.get("genre") or None,
            director=row.get("director") or None,
            producers=row.get("producers") or None,
            screenwriters=row.get("screenwriters") or None,
            imdb_rating=to_float_or_none(row.get("imdb_rating")),
            imdb_vote_count=to_int_or_none(row.get("imdb_vote_count")),
            running_time_minutes=to_int_or_none(row.get("running_time_minutes")),
        )

        if rows_affected > 0:
            updated += 1
        else:
            no_match_in_db += 1

    print("--- Summary ---")
    print(f"Updated in movies.db: {updated}")
    print(f"No matching tmdb_id in movies.db: {no_match_in_db}")
    print(f"Skipped (missing tmdb_id): {skipped_no_tmdb_id}")
    print(f"Total rows in CSV: {len(rows)}")


if __name__ == "__main__":
    main()