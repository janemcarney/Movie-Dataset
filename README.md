# Movie Dataset

This repository contains the code used to create a comprehensive movie dataset by combining information from the **TMDB API**, **Rotten Tomatoes**, **Wikidata**, and the **publicly available IMDb datasets**.

The scripts in this repository initialize a movie database, import movie metadata from TMDB, enrich missing information using additional sources, merge the collected results, and export the final dataset as a CSV.

## Setup

Clone the repository:

```bash
git clone <NEW_REPOSITORY_URL>
cd Movie-Dataset
```

### Create a Virtual Environment

#### Mac/Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

#### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## TMDB API Configuration

Create a `.env` file in the root of the project directory and add your TMDB bearer token (follow directions on https://developer.themoviedb.org/docs/authentication-application to obtain a token):

```text
TMDB_BEARER_TOKEN=your_token_here
```

Do not commit your `.env` file or API token to GitHub.

## Reproducing the Dataset

### 1. Initialize the Database

Create the initial database:

```bash
python setup_db.py
```

Test that the database was created correctly:

```bash
python test_database.py
```

The test should confirm that the sample *Barbie* movie row appears and is working properly.

### 2. Import Movies from TMDB

Import movie information from TMDB:

```bash
python import_tmdb_movies.py
```

View the movies currently stored in the database:

```bash
python view_movies.py
```

Export the database to a CSV:

```bash
python export_movies.py
```

This creates `movies.csv`. Running this command again will regenerate and overwrite the existing CSV.

### 3. Collect Rotten Tomatoes Data

Run the Rotten Tomatoes scraper:

```bash
python batch_scrape.py --input movies.csv --output rt_results.csv
```

The Rotten Tomatoes scrape can take a significant amount of time. For approximately 11,000 movies, the initial scrape may take up to 30 hours.

Merge the Rotten Tomatoes results into the movie database:

```bash
python merge_rt_results.py --input rt_results.csv --db movies.db
```

### 4. Collect Wikidata Information

Use Wikidata to fill in additional missing movie information:

```bash
python wikidata_scrape.py --db movies.db --output wikidata_results.csv
```

The Wikidata enrichment process is generally faster than the Rotten Tomatoes scrape.

Merge the Wikidata results into the database:

```bash
python merge_wikidata_results.py --input wikidata_results.csv --db movies.db
```

### 5. Download IMDb Public Datasets

Download the following five files from the [IMDb Non-Commercial Datasets](https://datasets.imdbws.com/) and place them directly in the project folder:

* `title.basics.tsv.gz`
* `title.ratings.tsv.gz`
* `title.crew.tsv.gz`
* `title.principals.tsv.gz`
* `name.basics.tsv.gz`

Leave these files compressed as `.gz` files.

The IMDb datasets are several GB combined and are not committed to GitHub. They should be excluded from version control through `.gitignore`.

### 6. Enrich the Database with IMDb Data

Run the IMDb dataset enrichment script:

```bash
python imdb_datasets_enrich.py --db movies.db --datasets-dir . --output imdb_datasets_results.csv
```

Merge the IMDb results into the database:

```bash
python merge_imdb_datasets_results.py --input imdb_datasets_results.csv --db movies.db
```

### 7. Export the Final Dataset

After all data sources have been merged, regenerate the final CSV:

```bash
python export_movies.py
```

This creates the final `movies.csv` containing the information collected from the available data sources.

### 8. Merge Additional Rotten Tomatoes Movie Data

Run:

```bash
python merge_rt_movies.py
```

## Data Sources

The dataset is constructed using information from:

* [TMDB](https://www.themoviedb.org/)
* Rotten Tomatoes
* [Wikidata](https://www.wikidata.org/)
* [IMDb Non-Commercial Datasets](https://datasets.imdbws.com/)

Each source contributes different metadata fields and is used to supplement missing information where possible.

## Important Files

* `setup_db.py` — initializes the movie database.
* `test_database.py` — tests that the database is functioning correctly.
* `import_tmdb_movies.py` — imports movie information from TMDB.
* `view_movies.py` — displays movie records from the database.
* `export_movies.py` — exports the database to `movies.csv`.
* `batch_scrape.py` — collects Rotten Tomatoes information.
* `merge_rt_results.py` — merges Rotten Tomatoes results into the database.
* `wikidata_scrape.py` — collects additional movie metadata from Wikidata.
* `merge_wikidata_results.py` — merges Wikidata results into the database.
* `imdb_datasets_enrich.py` — processes the publicly available IMDb datasets.
* `merge_imdb_datasets_results.py` — merges IMDb information into the database.
* `merge_rt_movies.py` — performs the final Rotten Tomatoes movie merge.

## Notes

Intermediate files such as the IMDb datasets and scraping outputs can be large and should not be committed to the repository.

The runtime of the full dataset-generation process depends on the number of movies being processed and the availability of the external data sources. In particular, the Rotten Tomatoes scraping step may take many hours to complete.
