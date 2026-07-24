import sqlite3


class MovieDatabase:
    def __init__(self, db_name="movies.db"):
        self.db_name = db_name

    def connect(self):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def create_table(self):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            tmdb_id INTEGER UNIQUE,
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

        # Add tmdb_id to an older existing table.
        cursor.execute("PRAGMA table_info(movies);")
        columns = [column["name"] for column in cursor.fetchall()]

        if "tmdb_id" not in columns:
            cursor.execute("""
            ALTER TABLE movies
            ADD COLUMN tmdb_id INTEGER;
            """)

        cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_movies_tmdb_id
        ON movies(tmdb_id);
        """)

        conn.commit()
        conn.close()

    def insert_movie(self, movie):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT OR IGNORE INTO movies (
            tmdb_id,
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
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?
        );
        """, (
            movie.get("tmdb_id"),
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

        cursor.execute("SELECT * FROM movies ORDER BY id;")
        rows = cursor.fetchall()

        conn.close()
        return rows

    def get_movies_by_title(self, title):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM movies
            WHERE title = ?
            ORDER BY release_date;
            """,
            (title,)
        )

        rows = cursor.fetchall()

        conn.close()
        return rows

    def update_revenue_and_budget(
        self,
        imdb_id,
        revenue,
        production_budget
    ):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
        UPDATE movies
        SET
            revenue = COALESCE(?, revenue),
            production_budget = COALESCE(
                ?,
                production_budget
            )
        WHERE imdb_id = ?;
        """, (
            revenue,
            production_budget,
            imdb_id
        ))

        updated_rows = cursor.rowcount

        conn.commit()
        conn.close()

        return updated_rows
    
    def update_rotten_tomatoes_data(self, tmdb_id, rotten_tomatoes_url, audience_rating, critics_rating, mpaa_rating):
            conn = self.connect()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE movies
                    SET rotten_tomatoes_url = ?,
                        rotten_tomatoes_audience_rating = ?,
                        rotten_tomatoes_critics_rating = ?,
                        mpaa_rating = ?
                    WHERE tmdb_id = ?
                """, (rotten_tomatoes_url, audience_rating, critics_rating, mpaa_rating, tmdb_id))
                
                rows_affected = cursor.rowcount
                conn.commit()
                return rows_affected
            except sqlite3.IntegrityError:
                conn.rollback()  # Instantly release transaction lock on duplicate URL
                raise
            finally:
                conn.close()

    def has_tmdb_movie(self, tmdb_id):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT 1
            FROM movies
            WHERE tmdb_id = ?
            LIMIT 1;
            """,
            (tmdb_id,)
        )

        exists = cursor.fetchone() is not None

        conn.close()
        return exists

    def save_tmdb_movie(self, movie):
        conn = self.connect()
        cursor = conn.cursor()

        tmdb_id = movie.get("tmdb_id")
        imdb_id = movie.get("imdb_id") or None

        # An existing row may already have the same IMDb ID.
        if imdb_id:
            cursor.execute("""
            UPDATE movies
            SET
                tmdb_id = COALESCE(tmdb_id, ?),
                revenue = COALESCE(revenue, ?),
                production_budget = COALESCE(
                    production_budget,
                    ?
                ),
                release_date = COALESCE(
                    release_date,
                    ?
                ),
                mpaa_rating = COALESCE(
                    mpaa_rating,
                    ?
                ),
                running_time_minutes = COALESCE(
                    running_time_minutes,
                    ?
                ),
                genre = COALESCE(genre, ?),
                director = COALESCE(director, ?),
                producers = COALESCE(producers, ?),
                screenwriters = COALESCE(
                    screenwriters,
                    ?
                )
            WHERE imdb_id = ?;
            """, (
                tmdb_id,
                movie.get("revenue"),
                movie.get("production_budget"),
                movie.get("release_date"),
                movie.get("mpaa_rating"),
                movie.get("running_time_minutes"),
                movie.get("genre"),
                movie.get("director"),
                movie.get("producers"),
                movie.get("screenwriters"),
                imdb_id
            ))

            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                return "updated"

        cursor.execute("""
        INSERT OR IGNORE INTO movies (
            tmdb_id,
            imdb_id,
            title,
            revenue,
            production_budget,
            release_date,
            mpaa_rating,
            running_time_minutes,
            genre,
            director,
            producers,
            screenwriters
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            tmdb_id,
            imdb_id,
            movie.get("title"),
            movie.get("revenue"),
            movie.get("production_budget"),
            movie.get("release_date"),
            movie.get("mpaa_rating"),
            movie.get("running_time_minutes"),
            movie.get("genre"),
            movie.get("director"),
            movie.get("producers"),
            movie.get("screenwriters")
        ))

        inserted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        if inserted:
            return "inserted"

        return "skipped"