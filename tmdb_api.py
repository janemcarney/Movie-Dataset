import os
import time

import requests
from dotenv import load_dotenv


load_dotenv()

BASE_URL = "https://api.themoviedb.org/3"
TMDB_BEARER_TOKEN = os.getenv("TMDB_BEARER_TOKEN")



if not TMDB_BEARER_TOKEN:
    raise RuntimeError(
        "TMDB_BEARER_TOKEN is not set."
    )

HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {TMDB_BEARER_TOKEN}"
}


def get_headers():
    if not TMDB_BEARER_TOKEN:
        raise ValueError(
            "Missing TMDB_BEARER_TOKEN. Add it to your .env file."
        )

    return {
        "Authorization": f"Bearer {TMDB_BEARER_TOKEN}",
        "accept": "application/json"
    }


def make_request(endpoint, params=None):
    url = f"{BASE_URL}{endpoint}"

    for attempt in range(5):
        response = requests.get(
            url,
            headers=get_headers(),
            params=params,
            timeout=30
        )

        if response.status_code == 404:
            return None

        if response.status_code == 429:
            retry_after = int(
                response.headers.get("Retry-After", "2")
            )

            print(
                f"TMDB rate limit reached. "
                f"Pausing for {retry_after} seconds."
            )

            time.sleep(retry_after)
            continue

        response.raise_for_status()
        return response.json()

    raise RuntimeError(
        f"TMDB request failed after several attempts: {endpoint}"
    )


def find_movie_by_imdb_id(imdb_id):
    data = make_request(
        f"/find/{imdb_id}",
        params={"external_source": "imdb_id"}
    )

    if data is None:
        return None

    movie_results = data.get("movie_results", [])

    if not movie_results:
        return None

    return movie_results[0]


def get_movie_details(tmdb_id):
    return make_request(
        f"/movie/{tmdb_id}",
        params={
            "language": "en-US",
            "append_to_response": (
                "external_ids,credits,release_dates"
            )
        }
    )



session = requests.Session()


def find_tmdb_movie(imdb_id, max_attempts=5):
    """
    Returns:
        ("movie", movie_result) if TMDB identifies it as a movie
        ("tv", None) for a TV series
        ("tv_episode", None) for a TV episode
        ("tv_season", None) for a TV season
        ("not_found", None) if TMDB has no matching result
        ("request_error", None) after repeated connection failures
    """

    url = f"https://api.themoviedb.org/3/find/{imdb_id}"
    params = {"external_source": "imdb_id"}

    for attempt in range(1, max_attempts + 1):
        try:
            response = session.get(
                url,
                headers=HEADERS,
                params=params,
                timeout=(10, 30)
            )

            if response.status_code == 429:
                wait_time = int(response.headers.get("Retry-After", 10))
                time.sleep(wait_time)
                continue

            response.raise_for_status()
            data = response.json()

            movie_results = data.get("movie_results", [])
            tv_results = data.get("tv_results", [])
            episode_results = data.get("tv_episode_results", [])
            season_results = data.get("tv_season_results", [])

            # Only accept an unambiguous movie result
            if movie_results and not (
                tv_results or episode_results or season_results
            ):
                return "movie", movie_results[0]

            if tv_results:
                return "tv", None

            if episode_results:
                return "tv_episode", None

            if season_results:
                return "tv_season", None

            return "not_found", None

        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError
        ):
            if attempt == max_attempts:
                return "request_error", None

            time.sleep(min(60, 2 ** attempt))

        except requests.exceptions.RequestException:
            return "request_error", None

    return "request_error", None


def unique_names(people, accepted_jobs):
    names = []

    for person in people:
        if person.get("job") in accepted_jobs:
            name = person.get("name")

            if name and name not in names:
                names.append(name)

    return ", ".join(names) if names else None


def get_us_certification(release_dates):
    for country in release_dates.get("results", []):
        if country.get("iso_3166_1") != "US":
            continue

        releases = country.get("release_dates", [])

        # Prefer a normal theatrical certification.
        preferred_types = [3, 2, 4, 5, 6, 1]

        for release_type in preferred_types:
            for release in releases:
                certification = (
                    release.get("certification") or ""
                ).strip()

                if (
                    release.get("type") == release_type
                    and certification
                ):
                    return certification

    return None


def get_full_movie_data(tmdb_id):
    details = get_movie_details(tmdb_id)

    if details is None:
        return None

    credits = details.get("credits", {})
    crew = credits.get("crew", [])

    external_ids = details.get("external_ids", {})

    genres = [
        genre["name"]
        for genre in details.get("genres", [])
        if genre.get("name")
    ]

    title = (
        details.get("title")
        or details.get("original_title")
        or f"TMDB Movie {tmdb_id}"
    )

    return {
        "tmdb_id": tmdb_id,
        "imdb_id": (
            external_ids.get("imdb_id")
            or details.get("imdb_id")
        ),
        "title": title,
        "revenue": details.get("revenue") or None,
        "production_budget": details.get("budget") or None,
        "release_date": details.get("release_date") or None,
        "mpaa_rating": get_us_certification(
            details.get("release_dates", {})
        ),
        "running_time_minutes": details.get("runtime") or None,
        "genre": ", ".join(genres) if genres else None,
        "director": unique_names(
            crew,
            {"Director"}
        ),
        "producers": unique_names(
            crew,
            {"Producer"}
        ),
        "screenwriters": unique_names(
            crew,
            {"Screenplay", "Writer", "Story"}
        )
    }


def get_revenue_and_budget(imdb_id):
    movie = find_movie_by_imdb_id(imdb_id)

    if movie is None:
        return None

    details = get_movie_details(movie["id"])

    if details is None:
        return None

    return {
        "revenue": details.get("revenue") or None,
        "production_budget": details.get("budget") or None
    }


