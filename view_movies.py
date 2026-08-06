from movie_database import MovieDatabase


db = MovieDatabase()
movies = db.get_all_movies()

print(f"Found {len(movies)} movie(s).")

for movie in movies:
    print("\n" + "=" * 50)
    print(f"Database ID: {movie['id']}")
    print(f"TMDB ID: {movie['tmdb_id']}")
    print(f"IMDb ID: {movie['imdb_id']}")
    print(f"Title: {movie['title']}")
    print(f"Release date: {movie['release_date']}")
    print(f"Runtime: {movie['running_time_minutes']} minutes")
    print(f"Genre: {movie['genre']}")
    print(f"Director: {movie['director']}")
    print(f"Producer(s): {movie['producers']}")
    print(f"Screenwriter(s): {movie['screenwriters']}")
    print(f"MPAA rating: {movie['mpaa_rating']}")
    print(f"Revenue: {movie['revenue']}")
    print(f"Production budget: {movie['production_budget']}")