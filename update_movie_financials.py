import time

from movie_database import MovieDatabase
from tmdb_api import get_revenue_and_budget


def main():
    db = MovieDatabase()
    db.create_table()

    movies = db.get_movies_missing_financials()

    print(f"Found {len(movies)} movie(s) to update.")

    updated_count = 0
    not_found_count = 0
    error_count = 0

    for movie in movies:
        imdb_id = movie["imdb_id"]
        title = movie["title"]

        print(f"\nSearching for {title} ({imdb_id})...")

        try:
            financials = get_revenue_and_budget(imdb_id)

            if financials is None:
                print("Movie not found on TMDB.")
                not_found_count += 1
                continue

            updated_rows = db.update_revenue_and_budget(
                imdb_id,
                financials["revenue"],
                financials["production_budget"]
            )

            if updated_rows == 0:
                print("No matching database row was updated.")
            else:
                print(
                    f"Revenue: {financials['revenue']}"
                )
                print(
                    "Production budget: "
                    f"{financials['production_budget']}"
                )

                updated_count += 1

            time.sleep(0.1)

        except Exception as error:
            print(f"Error updating {title}: {error}")
            error_count += 1

    print("\nFinished updating movies.")
    print(f"Updated: {updated_count}")
    print(f"Not found: {not_found_count}")
    print(f"Errors: {error_count}")


if __name__ == "__main__":
    main()