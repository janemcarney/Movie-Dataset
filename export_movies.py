import csv
import sqlite3


connection = sqlite3.connect("movies.db")
connection.row_factory = sqlite3.Row

cursor = connection.execute("""
SELECT *
FROM movies
ORDER BY id;
""")

movies = cursor.fetchall()

if not movies:
    print("There are no movies to export.")
else:
    column_names = movies[0].keys()

    with open(
        "movies.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=column_names
        )

        writer.writeheader()

        for movie in movies:
            writer.writerow(dict(movie))

    print(f"Exported {len(movies)} movies to movies.csv.")

connection.close()