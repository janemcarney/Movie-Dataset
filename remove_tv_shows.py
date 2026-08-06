import os
import shutil
import sqlite3
import time
from datetime import datetime

import requests
from dotenv import load_dotenv


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

DATABASE_PATH = "movies.db"
TABLE_NAME = "movies"

# Keep this False for the first run.
# Change it to True only after reviewing the results.
APPLY_DELETE = False

# Pause slightly between TMDB requests.
REQUEST_DELAY_SECONDS = 0.25


# --------------------------------------------------
# LOAD TMDB TOKEN
# --------------------------------------------------

load_dotenv()

TMDB_BEARER_TOKEN = os.getenv("TMDB_BEARER_TOKEN")

if not TMDB_BEARER_TOKEN:
    raise RuntimeError(
        "TMDB_BEARER_TOKEN was not found. "
        "Make sure it is listed in your .env file."
    )


# --------------------------------------------------
# TMDB REQUEST SETUP
# --------------------------------------------------

session = requests.Session()

session.headers.update(
    {
        "Authorization": f"Bearer {TMDB_BEARER_TOKEN}",
        "accept": "application/json",
    }
)


def classify_imdb_id(imdb_id: str) -> str:
    """
    Classify an IMDb ID using TMDB.

    Returns:
        movie
        tv
        tv_episode
        tv_season
        ambiguous
        unknown
    """

    imdb_id = imdb_id.strip()

    url = f"https://api.themoviedb.org/3/find/{imdb_id}"

    response = session.get(
        url,
        params={"external_source": "imdb_id"},
        timeout=30,
    )

    response.raise_for_status()
    data = response.json()

    result_types = []

    if data.get("movie_results"):
        result_types.append("movie")

    if data.get("tv_results"):
        result_types.append("tv")

    if data.get("tv_episode_results"):
        result_types.append("tv_episode")

    if data.get("tv_season_results"):
        result_types.append("tv_season")

    if len(result_types) == 1:
        return result_types[0]

    if len(result_types) > 1:
        return "ambiguous"

    return "unknown"


def get_database_columns(connection: sqlite3.Connection) -> set[str]:
    """Return all column names in the movies table."""

    cursor = connection.execute(
        f'PRAGMA table_info("{TABLE_NAME}")'
    )

    return {row[1] for row in cursor.fetchall()}


def main() -> None:
    if not os.path.exists(DATABASE_PATH):
        raise FileNotFoundError(
            f"Could not find {DATABASE_PATH}."
        )

    with sqlite3.connect(DATABASE_PATH) as connection:
        columns = get_database_columns(connection)

        required_columns = {"title", "imdb_id"}
        missing_columns = required_columns - columns

        if missing_columns:
            raise RuntimeError(
                "The movies table is missing these required columns: "
                + ", ".join(sorted(missing_columns))
            )

        rows = connection.execute(
            f"""
            SELECT
                rowid,
                title,
                imdb_id
            FROM "{TABLE_NAME}"
            WHERE imdb_id IS NOT NULL
              AND TRIM(imdb_id) != ''
            """
        ).fetchall()

        total_database_rows = connection.execute(
            f'SELECT COUNT(*) FROM "{TABLE_NAME}"'
        ).fetchone()[0]

    print(f"Total rows in database: {total_database_rows}")
    print(f"Rows with IMDb IDs to check: {len(rows)}")
    print()

    tv_rows = []
    movie_rows = []
    unknown_rows = []
    ambiguous_rows = []
    failed_rows = []

    # Avoid repeated API calls if duplicate IMDb IDs exist.
    classification_cache = {}

    for index, (rowid, title, imdb_id) in enumerate(rows, start=1):
        imdb_id = imdb_id.strip()

        try:
            if imdb_id in classification_cache:
                media_type = classification_cache[imdb_id]
            else:
                media_type = classify_imdb_id(imdb_id)
                classification_cache[imdb_id] = media_type
                time.sleep(REQUEST_DELAY_SECONDS)

            

            if media_type != "movie":
                print(f"[{index}/{len(rows)}] {title} ({imdb_id}): {media_type}")

            if media_type == "movie":
                movie_rows.append(
                    (rowid, title, imdb_id, media_type)
                )

            elif media_type in {
                "tv",
                "tv_episode",
                "tv_season",
            }:
                tv_rows.append(
                    (rowid, title, imdb_id, media_type)
                )

            elif media_type == "ambiguous":
                ambiguous_rows.append(
                    (rowid, title, imdb_id, media_type)
                )

            else:
                unknown_rows.append(
                    (rowid, title, imdb_id, media_type)
                )

        except requests.RequestException as error:
            print(f"    ERROR: {error}")

            failed_rows.append(
                (rowid, title, imdb_id, str(error))
            )

    print()
    print("----------------------------------------")
    print("CLASSIFICATION COMPLETE")
    print("----------------------------------------")
    print(f"Movies: {len(movie_rows)}")
    print(f"TV records: {len(tv_rows)}")
    print(f"Unknown: {len(unknown_rows)}")
    print(f"Ambiguous: {len(ambiguous_rows)}")
    print(f"Failed requests: {len(failed_rows)}")

    if tv_rows:
        print()
        print("----------------------------------------")
        print("TV RECORDS FOUND")
        print("----------------------------------------")

        for _, title, imdb_id, media_type in tv_rows:
            print(
                f"- {title} | {imdb_id} | {media_type}"
            )

    if unknown_rows:
        print()
        print("----------------------------------------")
        print("UNKNOWN RECORDS — WILL NOT BE DELETED")
        print("----------------------------------------")

        for _, title, imdb_id, _ in unknown_rows:
            print(f"- {title} | {imdb_id}")

    if ambiguous_rows:
        print()
        print("----------------------------------------")
        print("AMBIGUOUS RECORDS — WILL NOT BE DELETED")
        print("----------------------------------------")

        for _, title, imdb_id, _ in ambiguous_rows:
            print(f"- {title} | {imdb_id}")

    if failed_rows:
        print()
        print("----------------------------------------")
        print("FAILED REQUESTS — WILL NOT BE DELETED")
        print("----------------------------------------")

        for _, title, imdb_id, error in failed_rows:
            print(f"- {title} | {imdb_id} | {error}")

    if not APPLY_DELETE:
        print()
        print("----------------------------------------")
        print("PREVIEW MODE")
        print("----------------------------------------")
        print("Nothing was deleted.")
        print(
            "Review the TV records above. To delete them, "
            "change APPLY_DELETE = False to APPLY_DELETE = True "
            "and run the script again."
        )
        return

    if not tv_rows:
        print()
        print("No TV records were found, so nothing was deleted.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = (
        f"movies_before_tv_cleanup_{timestamp}.db"
    )

    shutil.copy2(DATABASE_PATH, backup_path)

    print()
    print(f"Backup created: {backup_path}")

    rowids_to_delete = [
        (rowid,)
        for rowid, _, _, _ in tv_rows
    ]

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.executemany(
            f"""
            DELETE FROM "{TABLE_NAME}"
            WHERE rowid = ?
            """,
            rowids_to_delete,
        )

        connection.commit()

        remaining_rows = connection.execute(
            f'SELECT COUNT(*) FROM "{TABLE_NAME}"'
        ).fetchone()[0]

    print(f"Deleted {len(tv_rows)} TV records.")
    print(f"Rows remaining in database: {remaining_rows}")


if __name__ == "__main__":
    main()