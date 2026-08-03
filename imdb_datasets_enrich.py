"""
imdb_datasets_enrich.py

Fills in missing genre, director, producers, screenwriters, imdb_rating,
imdb_vote_count, and running_time_minutes using IMDb's official
non-commercial datasets (https://datasets.imdbws.com/), matched by
imdb_id (tconst) — exact match, no fuzzy matching.

Download these 5 files first, into the same folder as this script
(leave them gzipped, this script reads them compressed directly):
    https://datasets.imdbws.com/title.basics.tsv.gz
    https://datasets.imdbws.com/title.ratings.tsv.gz
    https://datasets.imdbws.com/title.crew.tsv.gz
    https://datasets.imdbws.com/title.principals.tsv.gz
    https://datasets.imdbws.com/name.basics.tsv.gz

These are large files (name.basics and title.principals especially).
This script streams through each one line-by-line rather than loading
them fully into memory, filtering down to just your ~11,000 movies as
it goes.

Usage:
    python3 imdb_datasets_enrich.py --db movies.db --output imdb_datasets_results.csv
"""

import csv
import gzip
import argparse
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger("imdb_datasets_enrich")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

NULL = "\\N"

OUTPUT_FIELDS = [
    "tmdb_id", "imdb_id", "title",
    "genre", "director", "producers", "screenwriters",
    "imdb_rating", "imdb_vote_count", "running_time_minutes",
]


def get_target_movies(db_path: str) -> dict:
    """Returns {tconst: {tmdb_id, title}} for every movie with a usable imdb_id."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tmdb_id, imdb_id, title FROM movies
        WHERE imdb_id IS NOT NULL AND TRIM(imdb_id) != '';
    """)
    targets = {}
    for row in cursor.fetchall():
        targets[row["imdb_id"]] = {"tmdb_id": row["tmdb_id"], "title": row["title"]}
    conn.close()
    return targets


def open_tsv_gz(path: Path):
    return gzip.open(path, "rt", encoding="utf-8", newline="")


def stream_tsv(path: Path):
    """Yields dict rows from a gzipped IMDb TSV file, using its own header line."""
    with open_tsv_gz(path) as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            yield row


def val_or_none(v):
    return None if v in (None, "", NULL) else v


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="movies.db", help="Path to movies.db")
    parser.add_argument("--datasets-dir", default=".", help="Folder containing the downloaded .tsv.gz files")
    parser.add_argument("--output", default="imdb_datasets_results.csv", help="Path to output CSV")
    args = parser.parse_args()

    datasets_dir = Path(args.datasets_dir)
    paths = {
        "basics": datasets_dir / "title.basics.tsv.gz",
        "ratings": datasets_dir / "title.ratings.tsv.gz",
        "crew": datasets_dir / "title.crew.tsv.gz",
        "principals": datasets_dir / "title.principals.tsv.gz",
        "names": datasets_dir / "name.basics.tsv.gz",
    }
    for name, p in paths.items():
        if not p.exists():
            raise FileNotFoundError(
                f"Missing {p} — download it from https://datasets.imdbws.com/{p.name} first."
            )

    targets = get_target_movies(args.db)
    logger.info(f"Target movies with imdb_id: {len(targets)}")

    result = {tconst: {} for tconst in targets}

    # --- title.ratings.tsv.gz: imdb_rating, imdb_vote_count ---
    logger.info("Processing title.ratings.tsv.gz ...")
    count = 0
    for row in stream_tsv(paths["ratings"]):
        tconst = row["tconst"]
        if tconst in result:
            result[tconst]["imdb_rating"] = val_or_none(row.get("averageRating"))
            result[tconst]["imdb_vote_count"] = val_or_none(row.get("numVotes"))
            count += 1
    logger.info(f"  matched {count} ratings rows")

    # --- title.basics.tsv.gz: genre, running_time_minutes ---
    logger.info("Processing title.basics.tsv.gz ...")
    count = 0
    for row in stream_tsv(paths["basics"]):
        tconst = row["tconst"]
        if tconst in result:
            genres = val_or_none(row.get("genres"))
            result[tconst]["genre"] = genres.replace(",", ", ") if genres else None
            result[tconst]["running_time_minutes"] = val_or_none(row.get("runtimeMinutes"))
            count += 1
    logger.info(f"  matched {count} basics rows")

    # --- title.crew.tsv.gz: directors, writers (nconst lists) ---
    logger.info("Processing title.crew.tsv.gz ...")
    needed_nconsts = set()
    count = 0
    for row in stream_tsv(paths["crew"]):
        tconst = row["tconst"]
        if tconst in result:
            directors = val_or_none(row.get("directors"))
            writers = val_or_none(row.get("writers"))
            director_ids = directors.split(",") if directors else []
            writer_ids = writers.split(",") if writers else []
            result[tconst]["_director_ids"] = director_ids
            result[tconst]["_writer_ids"] = writer_ids
            needed_nconsts.update(director_ids)
            needed_nconsts.update(writer_ids)
            count += 1
    logger.info(f"  matched {count} crew rows")

    # --- title.principals.tsv.gz: producers (not in title.crew.tsv.gz) ---
    logger.info("Processing title.principals.tsv.gz (large file, this takes a while) ...")
    count = 0
    for row in stream_tsv(paths["principals"]):
        tconst = row["tconst"]
        if tconst in result and row.get("category") == "producer":
            nconst = row["nconst"]
            result[tconst].setdefault("_producer_ids", []).append(nconst)
            needed_nconsts.add(nconst)
            count += 1
    logger.info(f"  matched {count} producer credit rows")

    # --- name.basics.tsv.gz: resolve nconst -> primaryName for everyone needed above ---
    logger.info(f"Processing name.basics.tsv.gz to resolve {len(needed_nconsts)} names (large file, this takes a while) ...")
    names = {}
    for row in stream_tsv(paths["names"]):
        nconst = row["nconst"]
        if nconst in needed_nconsts:
            names[nconst] = row["primaryName"]
    logger.info(f"  resolved {len(names)} names")

    # --- Assemble final rows ---
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for tconst, info in targets.items():
            r = result.get(tconst, {})
            director_names = ", ".join(names[i] for i in r.get("_director_ids", []) if i in names)
            writer_names = ", ".join(names[i] for i in r.get("_writer_ids", []) if i in names)
            producer_names = ", ".join(names[i] for i in r.get("_producer_ids", []) if i in names)

            writer.writerow({
                "tmdb_id": info["tmdb_id"],
                "imdb_id": tconst,
                "title": info["title"],
                "genre": r.get("genre") or "",
                "director": director_names,
                "producers": producer_names,
                "screenwriters": writer_names,
                "imdb_rating": r.get("imdb_rating") or "",
                "imdb_vote_count": r.get("imdb_vote_count") or "",
                "running_time_minutes": r.get("running_time_minutes") or "",
            })

    logger.info(f"Done. Wrote {len(targets)} rows to {args.output}")


if __name__ == "__main__":
    main()