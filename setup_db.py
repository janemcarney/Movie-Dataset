import sqlite3

conn = sqlite3.connect("movies.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    imdb_id TEXT UNIQUE,
    rotten_tomatoes_url TEXT UNIQUE,

    title TEXT NOT NULL,

    us_canada_gross INTEGER,
    worldwide_gross INTEGER,
    production_budget INTEGER,

    release_date TEXT,
    mpaa_rating TEXT,
    running_time_minutes INTEGER,
    distributor TEXT,

    genre TEXT,
    director TEXT,
    producers TEXT,
    screenwriters TEXT,

    rotten_tomatoes_audience_rating INTEGER,
    rotten_tomatoes_critics_rating INTEGER,
    imdb_rating REAL,
    imdb_vote_count INTEGER
);
""")

conn.commit()
conn.close()

print("Database and movies table created.")