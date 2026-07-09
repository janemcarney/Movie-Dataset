import sqlite3


class MovieDatabase:
    def __init__(self, db_name="movies.db"):
        self.db_name = db_name

    def connect(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def create_table(self):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            imdb_id TEXT UNIQUE,
            rotten_tomatoes_url TEXT UNIQUE,

            title TEXT NOT NULL,

            revenue INTEGER,
            production_budget INTEGER,

            release_date TEXT,
            mpaa_rating TEXT,
            running_time_minutes INTEGER,
            distributor TEXT,

            genre TEXT,
            director TEXT,
            producers TEXT,
            screenwriters TEXT,
            awards TEXT,

            rotten_tomatoes_audience_rating INTEGER,
            rotten_tomatoes_critics_rating INTEGER,
            imdb_rating REAL,
            imdb_vote_count INTEGER
        );
        """)

        conn.commit()
        conn.close()

    def insert_movie(self, movie):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT OR IGNORE INTO movies (
            imdb_id,
            rotten_tomatoes_url,
            title,
            revenue,
            production_budget,
            release_date,
            mpaa_rating,
            running_time_minutes,
            distributor,
            genre,
            director,
            producers,
            screenwriters,
            awards,
            rotten_tomatoes_audience_rating,
            rotten_tomatoes_critics_rating,
            imdb_rating,
            imdb_vote_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            movie.get("imdb_id"),
            movie.get("rotten_tomatoes_url"),
            movie.get("title"),
            movie.get("revenue"),
            movie.get("production_budget"),
            movie.get("release_date"),
            movie.get("mpaa_rating"),
            movie.get("running_time_minutes"),
            movie.get("distributor"),
            movie.get("genre"),
            movie.get("director"),
            movie.get("producers"),
            movie.get("screenwriters"),
            movie.get("awards"),
            movie.get("rotten_tomatoes_audience_rating"),
            movie.get("rotten_tomatoes_critics_rating"),
            movie.get("imdb_rating"),
            movie.get("imdb_vote_count")
        ))

        conn.commit()
        conn.close()

    def get_all_movies(self):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM movies;")
        rows = cursor.fetchall()

        conn.close()
        return rows

    def get_movie_by_title(self, title):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM movies WHERE title = ?;", (title,))
        row = cursor.fetchone()

        conn.close()
        return row