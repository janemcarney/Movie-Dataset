from movie_database import MovieDatabase

db = MovieDatabase()
db.create_table()

movie = {
    "imdb_id": "tt1517268",
    "rotten_tomatoes_url": "https://www.rottentomatoes.com/m/barbie",
    "title": "Barbie",
    "us_canada_gross": 636200000,
    "worldwide_gross": 1446000000,
    "production_budget": 145000000,
    "release_date": "2023-07-21",
    "mpaa_rating": "PG-13",
    "running_time_minutes": 114,
    "distributor": "Warner Bros.",
    "genre": "Comedy, Fantasy",
    "director": "Greta Gerwig",
    "producers": "Margot Robbie, Tom Ackerley, Robbie Brenner",
    "screenwriters": "Greta Gerwig, Noah Baumbach",
    "awards": "Won 1 Oscar, 8 wins & 22 nominations total",
    "rotten_tomatoes_audience_rating": 83,
    "rotten_tomatoes_critics_rating": 88,
    "imdb_rating": 6.8,
    "imdb_vote_count": 400000
}

db.insert_movie(movie)

movies = db.get_all_movies()

for movie in movies:
    print(dict(movie))