import pandas as pd


# Load both CSV files.
# Reading tmdb_id as a string helps prevent matching problems.
movies = pd.read_csv("movies.csv", dtype={"tmdb_id": "string"})
rt_results = pd.read_csv("rt_results.csv", dtype={"tmdb_id": "string"})


# Create cleaned matching columns without changing the original titles or IDs.
movies["_title_key"] = (
    movies["title"]
    .astype("string")
    .str.strip()
    .str.casefold()
)

rt_results["_title_key"] = (
    rt_results["title"]
    .astype("string")
    .str.strip()
    .str.casefold()
)

movies["_tmdb_id_key"] = (
    movies["tmdb_id"]
    .astype("string")
    .str.strip()
    .str.replace(r"\.0$", "", regex=True)
)

rt_results["_tmdb_id_key"] = (
    rt_results["tmdb_id"]
    .astype("string")
    .str.strip()
    .str.replace(r"\.0$", "", regex=True)
)


# Keep only Rotten Tomatoes results where the scrape succeeded.
rt_ok = rt_results[
    rt_results["status"]
    .astype("string")
    .str.strip()
    .str.casefold()
    .eq("ok")
].copy()


# Keep only the matching columns and fields that should be imported.
rt_ok = rt_ok[
    [
        "_title_key",
        "_tmdb_id_key",
        "rt_url",
        "critics_score",
        "audience_score",
        "mpaa_rating",
    ]
]


# Rename the imported columns temporarily to avoid name conflicts.
rt_ok = rt_ok.rename(
    columns={
        "rt_url": "_new_rotten_tomatoes_url",
        "critics_score": "_new_critics_rating",
        "audience_score": "_new_audience_rating",
        "mpaa_rating": "_new_mpaa_rating",
    }
)


# Prevent one movie from being duplicated if rt_results contains
# multiple successful rows for the same title and TMDB ID.
rt_ok = rt_ok.drop_duplicates(
    subset=["_title_key", "_tmdb_id_key"],
    keep="last"
)


# Merge RT information into movies while keeping every movies.csv row.
movies = movies.merge(
    rt_ok,
    on=["_title_key", "_tmdb_id_key"],
    how="left",
    validate="many_to_one",
)


# Make sure the destination columns exist.
destination_columns = [
    "rotten_tomatoes_url",
    "rotten_tomatoes_critics_rating",
    "rotten_tomatoes_audience_rating",
    "mpaa_rating",
]

for column in destination_columns:
    if column not in movies.columns:
        movies[column] = pd.NA


# Update these fields whenever an "ok" RT result supplies a value.
movies["rotten_tomatoes_url"] = (
    movies["_new_rotten_tomatoes_url"]
    .combine_first(movies["rotten_tomatoes_url"])
)

movies["rotten_tomatoes_critics_rating"] = (
    movies["_new_critics_rating"]
    .combine_first(movies["rotten_tomatoes_critics_rating"])
)

movies["rotten_tomatoes_audience_rating"] = (
    movies["_new_audience_rating"]
    .combine_first(movies["rotten_tomatoes_audience_rating"])
)


# Only import the RT MPAA rating when movies.csv currently has no rating.
mpaa_is_blank = (
    movies["mpaa_rating"].isna()
    | movies["mpaa_rating"].astype("string").str.strip().eq("")
)

new_mpaa_exists = (
    movies["_new_mpaa_rating"].notna()
    & movies["_new_mpaa_rating"].astype("string").str.strip().ne("")
)

movies.loc[
    mpaa_is_blank & new_mpaa_exists,
    "mpaa_rating"
] = movies.loc[
    mpaa_is_blank & new_mpaa_exists,
    "_new_mpaa_rating"
]


# Count how many movies received Rotten Tomatoes matches.
matched_count = movies["_new_rotten_tomatoes_url"].notna().sum()


# Remove temporary merge columns.
movies = movies.drop(
    columns=[
        "_title_key",
        "_tmdb_id_key",
        "_new_rotten_tomatoes_url",
        "_new_critics_rating",
        "_new_audience_rating",
        "_new_mpaa_rating",
    ]
)


# Save to a new file first.
movies.to_csv(
    "movies_updated.csv",
    index=False,
    encoding="utf-8"
)

print(f"Matched {matched_count} movies with successful RT results.")
print("Saved the merged dataset to movies_updated.csv.")