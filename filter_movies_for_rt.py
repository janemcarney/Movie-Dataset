"""
filter_movies_for_rt.py

Filters a large TMDb-derived movie CSV down to a subset worth attempting
on Rotten Tomatoes.

This version filters on imdb_id presence — a rougher signal than
vote_count/popularity (which aren't available in this particular
export), but usable as-is: a movie having an IMDb entry at all
correlates loosely with being a real, notable release rather than an
obscure/unlisted title RT was never going to have anyway. It will let
through more of the long tail than a vote_count-based filter would, so
treat the estimated scrape time below as a lower bound, not a promise.

Usage:
    python3 filter_movies_for_rt.py --input tmdb_million.csv --output movies_for_rt.csv
    python3 filter_movies_for_rt.py --input tmdb_million.csv --output movies_for_rt.csv --require-release-date
"""

import csv
import argparse

# --- Adjust these to match your actual CSV column names ---
IMDB_ID_COLUMN = "imdb_id"
RELEASE_DATE_COLUMN = "release_date"
TITLE_COLUMN = "title"

SECONDS_PER_MOVIE = 5  # rough estimate: 2 requests + delay, matches earlier RT runs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to the large movie CSV")
    parser.add_argument("--output", required=True, help="Path to write the filtered CSV")
    parser.add_argument(
        "--require-release-date", action="store_true",
        help="Also require a non-empty release_date (extra, weaker signal on top of imdb_id)"
    )
    args = parser.parse_args()

    with open(args.input, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    total = len(rows)
    print(f"Total movies in input: {total}")

    if IMDB_ID_COLUMN not in fieldnames:
        raise ValueError(
            f"Column '{IMDB_ID_COLUMN}' not found. "
            f"Actual columns: {fieldnames}\n"
            f"Update IMDB_ID_COLUMN at the top of this script to match."
        )

    def keep(row):
        imdb_id = (row.get(IMDB_ID_COLUMN) or "").strip()
        if not imdb_id:
            return False

        if args.require_release_date:
            release_date = (row.get(RELEASE_DATE_COLUMN) or "").strip()
            if not release_date:
                return False

        return True

    filtered = [r for r in rows if keep(r)]

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered)

    kept = len(filtered)
    pct = kept / total * 100 if total else 0
    est_hours = (kept * SECONDS_PER_MOVIE) / 3600

    print(f"Kept: {kept} ({pct:.1f}% of total)")
    print(f"Estimated RT scrape time at this size: ~{est_hours:.1f} hours "
          f"({est_hours/24:.1f} days)")
    print("Note: this is a rougher filter than vote_count-based filtering would be — "
          "expect a higher not_found rate on RT than the earlier 11,197-movie run.")
    print(f"Written to: {args.output}")


if __name__ == "__main__":
    main()