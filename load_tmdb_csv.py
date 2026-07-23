"""
load_tmdb_csv.py

Loads movies.csv (your partner's TMDb export) into movies.db using
save_tmdb_movie(). Safe to run even if the data's already loaded —
save_tmdb_movie() either updates existing rows via COALESCE or does
INSERT OR IGNORE, so re-running this doesn't create duplicates or
overwrite anything already filled in.

Usage:
    python3 load_tmdb_csv.py --input movies.csv --db movies.db
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
    parser.add_argument("--input", required=True, help="Path to movies.csv")
    parser.add_argument("--db", default="movies.db", help="Path to movies.db")
    args = parser.parse_args()

    db = MovieDatabase(args.db)
    db.create_table()

    with open(args.input, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    inserted = updated = skipped = 0

    for row in rows:
        movie = {
            "tmdb_id": to_int_or_none(row.get("tmdb_id")),
            "imdb_id": row.get("imdb_id") or None,
            "title": row.get("title") or None,
            "revenue": to_int_or_none(row.get("revenue")),
            "production_budget": to_int_or_none(row.get("production_budget")),
            "release_date": row.get("release_date") or None,
            "mpaa_rating": row.get("mpaa_rating") or None,
            "running_time_minutes": to_int_or_none(row.get("running_time_minutes")),
            "genre": row.get("genre") or None,
            "director": row.get("director") or None,
            "producers": row.get("producers") or None,
            "screenwriters": row.get("screenwriters") or None,
        }

        result = db.save_tmdb_movie(movie)
        if result == "inserted":
            inserted += 1
        elif result == "updated":
            updated += 1
        else:
            skipped += 1

    print(f"Inserted: {inserted}")
    print(f"Updated: {updated}")
    print(f"Skipped (no imdb_id match, already existed): {skipped}")
    print(f"Total rows in CSV: {len(rows)}")


if __name__ == "__main__":
    main()