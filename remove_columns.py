import sqlite3

DATABASE_PATH = "movies.db"

columns_to_remove = ["awards", "distributor"]

with sqlite3.connect(DATABASE_PATH) as conn:
    cursor = conn.cursor()

    # Display the current columns
    cursor.execute("PRAGMA table_info(movies)")
    current_columns = {row[1] for row in cursor.fetchall()}

    for column in columns_to_remove:
        if column in current_columns:
            cursor.execute(f'ALTER TABLE movies DROP COLUMN "{column}"')
            print(f"Removed column: {column}")
        else:
            print(f"Column does not exist: {column}")

print("Database migration completed.")