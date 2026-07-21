import gzip
import json
import shutil
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from movie_database import MovieDatabase
from tmdb_api import get_full_movie_data


# Start small. Change this to None only after testing.
MAX_NEW_MOVIES = 10000

# Be respectful to the API.
REQUEST_DELAY_SECONDS = 0.3

EXPORT_DIRECTORY = Path("tmdb_exports")


def download_latest_movie_export():
    EXPORT_DIRECTORY.mkdir(exist_ok=True)

    today = datetime.now(timezone.utc).date()

    # Today's export may not be ready yet, so try recent dates.
    for days_ago in range(7):
        export_date = today - timedelta(days=days_ago)

        date_string = export_date.strftime("%m_%d_%Y")
        filename = f"movie_ids_{date_string}.json.gz"

        url = (
            "https://files.tmdb.org/p/exports/"
            f"{filename}"
        )

        output_path = EXPORT_DIRECTORY / filename

        if output_path.exists():
            print(f"Using existing export: {output_path}")
            return output_path

        print(f"Trying TMDB export for {export_date}...")

        response = requests.get(
            url,
            stream=True,
            timeout=120
        )

        if response.status_code == 404:
            continue

        response.raise_for_status()

        with output_path.open("wb") as output_file:
            shutil.copyfileobj(
                response.raw,
                output_file
            )

        print(f"Downloaded: {output_path}")
        return output_path

    raise RuntimeError(
        "Could not find a recent TMDB movie-ID export."
    )


def import_movies():
    db = MovieDatabase()
    db.create_table()

    export_path = download_latest_movie_export()

    attempted = 0
    inserted = 0
    updated = 0
    skipped = 0
    errors = 0

    with gzip.open(
        export_path,
        "rt",
        encoding="utf-8"
    ) as export_file:

        for line in export_file:
            export_record = json.loads(line)

            # Skip adult entries and video-only records.
            if export_record.get("adult"):
                continue

            if export_record.get("video"):
                continue

            tmdb_id = export_record.get("id")

            if tmdb_id is None:
                continue

            # This makes the importer resumable.
            if db.has_tmdb_movie(tmdb_id):
                continue

            if (
                MAX_NEW_MOVIES is not None
                and attempted >= MAX_NEW_MOVIES
            ):
                break

            attempted += 1

            print(
                f"\n[{attempted}] "
                f"Fetching TMDB movie {tmdb_id}..."
            )

            try:
                movie = get_full_movie_data(tmdb_id)

                if movie is None:
                    print("Movie details were unavailable.")
                    skipped += 1
                    continue

                result = db.save_tmdb_movie(movie)

                if result == "inserted":
                    inserted += 1
                elif result == "updated":
                    updated += 1
                else:
                    skipped += 1

                print(
                    f"{result.title()}: "
                    f"{movie['title']}"
                )

            except requests.RequestException as error:
                errors += 1
                print(f"Request error: {error}")

            except Exception as error:
                errors += 1
                print(f"Error: {error}")

            time.sleep(REQUEST_DELAY_SECONDS)

    print("\nImport complete.")
    print(f"API records attempted: {attempted}")
    print(f"New rows inserted: {inserted}")
    print(f"Existing rows updated: {updated}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")


if __name__ == "__main__":
    import_movies()