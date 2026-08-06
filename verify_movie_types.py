from movie_database import MovieDatabase
from tmdb_api import find_tmdb_movie


db = MovieDatabase()
movies = db.get_all_movies()

problems = 0

for movie in movies:
    imdb_id = movie["imdb_id"]

    if not imdb_id:
        print(f"Cannot verify: {movie['title']} has no IMDb ID")
        continue

    media_type, _ = find_tmdb_movie(imdb_id)

    if media_type != "movie":
        problems += 1
        print(
            f"CHECK: {movie['title']} "
            f"({imdb_id}) returned {media_type}"
        )

print()
print(f"Rows checked: {len(movies)}")
print(f"Possible non-movies: {problems}")