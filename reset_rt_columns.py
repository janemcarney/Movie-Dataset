"""
reset_rt_columns.py

Resets the RT-sourced columns in movies.db back to NULL, so a fresh
merge_rt_results.py run can actually take effect via COALESCE instead
of silently skipping rows that already have (possibly wrong, from an
earlier buggy scrape) data in them.

Only touches rotten_tomatoes_url, rotten_tomatoes_critics_rating, and
rotten_tomatoes_audience_rating — NOT mpaa_rating, since that field can
also come from TMDb directly and resetting it risks losing a
TMDb-sourced value that was never RT's to begin with.

Usage:
    python3 reset_rt_columns.py --db movies.db
"""

import argparse
from movie_database import MovieDatabase


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="movies.db", help="Path to movies.db")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    db = MovieDatabase(args.db)
    conn = db.connect()

    before = conn.execute(
        "SELECT COUNT(*) FROM movies WHERE rotten_tomatoes_critics_rating IS NOT NULL"
    ).fetchone()[0]
    print(f"{before} rows currently have rotten_tomatoes_critics_rating set.")

    if before == 0:
        print("Nothing to reset.")
        conn.close()
        return

    if not args.yes:
        confirm = input(
            f"This will clear rotten_tomatoes_url, rotten_tomatoes_critics_rating, "
            f"and rotten_tomatoes_audience_rating for {before} rows. Type 'yes' to continue: "
        )
        if confirm.strip().lower() != "yes":
            print("Cancelled.")
            conn.close()
            return

    conn.execute("""
        UPDATE movies
        SET
            rotten_tomatoes_url = NULL,
            rotten_tomatoes_critics_rating = NULL,
            rotten_tomatoes_audience_rating = NULL;
    """)
    conn.commit()
    conn.close()
    print(f"Reset complete. {before} rows cleared — ready for a fresh merge_rt_results.py run.")


if __name__ == "__main__":
    main()