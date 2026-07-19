"""
Discover NCAA women's volleyball roster URLs.

Input:
    data/raw/school_list.csv

Required columns:
    SCHOOL_NAME_OFFICIAL
    DIVISION
    CONFERENCE_CODE
    PRIMARY_CONFERENCE

Output:
    data/interim/roster_sources.csv
"""

from __future__ import annotations

import time
from urllib.parse import (
    parse_qs,
    unquote,
    urljoin,
    urlparse,
)

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.config import (
    HEADERS,
    REQUEST_DELAY,
    REQUEST_TIMEOUT,
    ROSTER_SOURCES_FILE,
    SCHOOL_LIST_FILE,
    SEASONS,
)


############################
# Settings
############################

SEARCH_URL = "https://html.duckduckgo.com/html/"

MAX_SEARCH_RESULTS = 8

SPORT_TERMS = (
    "women's volleyball",
    "womens volleyball",
    "volleyball",
)

ROSTER_TERMS = (
    "roster",
    "/roster",
)

EXCLUDED_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "maxpreps.com",
    "ncaa.com",
    "ncaa.org",
    "twitter.com",
    "wikipedia.org",
    "x.com",
    "youtube.com",
}


############################
# School loading
############################


def load_schools() -> pd.DataFrame:
    """Load and validate the NCAA school population file."""

    schools_df = pd.read_csv(
        SCHOOL_LIST_FILE
    )

    required_columns = {
        "SCHOOL_NAME_OFFICIAL",
        "DIVISION",
        "CONFERENCE_CODE",
        "PRIMARY_CONFERENCE",
    }

    missing_columns = (
        required_columns
        - set(schools_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "school_list.csv is missing required columns: "
            + ", ".join(
                sorted(missing_columns)
            )
        )

    schools_df = (
        schools_df[
            list(required_columns)
        ]
        .copy()
    )

    schools_df = schools_df[
        schools_df[
            "SCHOOL_NAME_OFFICIAL"
        ].notna()
    ].copy()

    schools_df[
        "SCHOOL_NAME_OFFICIAL"
    ] = (
        schools_df[
            "SCHOOL_NAME_OFFICIAL"
        ]
        .astype(str)
        .str.strip()
    )

    schools_df = schools_df[
        schools_df[
            "SCHOOL_NAME_OFFICIAL"
        ].ne("")
    ].copy()

    return schools_df


############################
# URL helpers
############################


def clean_search_result_url(
    href: str,
) -> str:
    """
    Convert DuckDuckGo redirect URLs into destination URLs.
    """

    if not href:
        return ""

    parsed = urlparse(href)

    query = parse_qs(
        parsed.query
    )

    if "uddg" in query:
        return unquote(
            query["uddg"][0]
        )

    return href


def get_domain(
    url: str,
) -> str:
    """Return normalized hostname."""

    hostname = (
        urlparse(url)
        .netloc
        .lower()
    )

    if hostname.startswith(
        "www."
    ):
        hostname = hostname[4:]

    return hostname


def is_excluded_domain(
    url: str,
) -> bool:
    """Reject obvious non-athletics sources."""

    domain = get_domain(url)

    return any(
        domain == excluded
        or domain.endswith(
            f".{excluded}"
        )
        for excluded
        in EXCLUDED_DOMAINS
    )


############################
# Search
############################


def search_web(
    session: requests.Session,
    query: str,
) -> list[str]:
    """
    Search DuckDuckGo HTML results.

    Returns destination URLs.
    """

    try:
        response = session.get(
            SEARCH_URL,
            params={
                "q": query,
            },
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

    except requests.RequestException as error:
        print(
            f"    Search failed: {error}"
        )
        return []

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    results: list[str] = []

    for link in soup.select(
        "a.result__a"
    ):
        href = (
            link.get("href")
            or ""
        )

        url = clean_search_result_url(
            href
        )

        if (
            not url
            or is_excluded_domain(url)
        ):
            continue

        if url not in results:
            results.append(url)

        if (
            len(results)
            >= MAX_SEARCH_RESULTS
        ):
            break

    return results


############################
# Page validation
############################


def fetch_page(
    session: requests.Session,
    url: str,
) -> requests.Response | None:
    """Fetch a page safely."""

    try:
        response = session.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )

        if (
            response.status_code
            != 200
        ):
            return None

        return response

    except requests.RequestException:
        return None


def looks_like_volleyball_page(
    response: requests.Response,
) -> bool:
    """
    Check whether a webpage appears related to
    women's volleyball.
    """

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    title = (
        soup.title.get_text(
            " ",
            strip=True,
        ).lower()
        if soup.title
        else ""
    )

    body_text = (
        soup.get_text(
            " ",
            strip=True,
        )
        .lower()
    )

    combined = (
        f"{title} {body_text}"
    )

    return any(
        term in combined
        for term in SPORT_TERMS
    )


def looks_like_roster_page(
    response: requests.Response,
) -> bool:
    """
    Check whether a webpage appears to be
    a player roster.
    """

    if not looks_like_volleyball_page(
        response
    ):
        return False

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    title = (
        soup.title.get_text(
            " ",
            strip=True,
        ).lower()
        if soup.title
        else ""
    )

    text = (
        soup.get_text(
            " ",
            strip=True,
        ).lower()
    )

    url = (
        response.url.lower()
    )

    roster_signal = (
        "roster" in title
        or "roster" in url
        or "roster" in text
    )

    player_fields = (
        "height",
        "position",
        "hometown",
        "class",
        "year",
    )

    player_signal_count = sum(
        field in text
        for field in player_fields
    )

    return (
        roster_signal
        and player_signal_count >= 2
    )


############################
# Roster link discovery
############################


def extract_roster_links(
    page_url: str,
    html: str,
) -> list[str]:
    """
    Find links containing 'roster' on
    a volleyball or athletics page.
    """

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    links: list[str] = []

    for anchor in soup.find_all(
        "a",
        href=True,
    ):
        href = str(
            anchor["href"]
        )

        text = (
            anchor.get_text(
                " ",
                strip=True,
            ).lower()
        )

        href_lower = (
            href.lower()
        )

        if (
            "roster" not in text
            and "roster"
            not in href_lower
        ):
            continue

        full_url = urljoin(
            page_url,
            href,
        )

        if (
            full_url
            not in links
        ):
            links.append(
                full_url
            )

    return links


def add_season_to_url(
    url: str,
    season: int,
) -> list[str]:
    """
    Generate reasonable historical roster
    variants from a discovered roster URL.
    """

    clean_url = (
        url.rstrip("/")
    )

    academic_year = (
        f"{season}-"
        f"{str(season + 1)[-2:]}"
    )

    candidates = [
        clean_url,
        f"{clean_url}/{season}",
        (
            f"{clean_url}/"
            f"{academic_year}"
        ),
        (
            f"{clean_url}/season/"
            f"{season}"
        ),
        (
            f"{clean_url}/season/"
            f"{academic_year}"
        ),
    ]

    unique_candidates = []

    for candidate in candidates:
        if (
            candidate
            not in unique_candidates
        ):
            unique_candidates.append(
                candidate
            )

    return unique_candidates


############################
# School discovery
############################


def discover_school_roster(
    session: requests.Session,
    school_name: str,
    season: int,
) -> dict[str, str]:
    """
    Discover one school's roster URL
    for one season.
    """

    search_queries = [
        (
            f'"{school_name}" '
            f'womens volleyball roster '
            f'{season}'
        ),
        (
            f'"{school_name}" '
            f'athletics womens volleyball'
        ),
    ]

    search_results: list[str] = []

    for query in search_queries:
        print(
            f"    Searching: {query}"
        )

        urls = search_web(
            session,
            query,
        )

        for url in urls:
            if (
                url
                not in search_results
            ):
                search_results.append(
                    url
                )

        time.sleep(
            REQUEST_DELAY
        )

    attempts: list[str] = []

    for result_url in search_results:
        response = fetch_page(
            session,
            result_url,
        )

        if response is None:
            attempts.append(
                f"fetch_failed:{result_url}"
            )
            continue

        final_url = response.url

        print(
            f"    Checking: {final_url}"
        )

        attempts.append(
            final_url
        )

        # Search result may already be
        # the exact roster page.
        if looks_like_roster_page(
            response
        ):
            return {
                "status": "found",
                "roster_url": final_url,
                "athletics_domain":
                    get_domain(
                        final_url
                    ),
                "discovery_method":
                    "search_result",
                "attempts":
                    " | ".join(
                        attempts
                    ),
            }

        # Otherwise, inspect links on the
        # page for roster pages.
        roster_links = (
            extract_roster_links(
                final_url,
                response.text,
            )
        )

        for roster_link in roster_links:
            for candidate in (
                add_season_to_url(
                    roster_link,
                    season,
                )
            ):
                candidate_response = (
                    fetch_page(
                        session,
                        candidate,
                    )
                )

                if (
                    candidate_response
                    is None
                ):
                    continue

                attempts.append(
                    candidate_response.url
                )

                if (
                    looks_like_roster_page(
                        candidate_response
                    )
                ):
                    return {
                        "status":
                            "found",
                        "roster_url":
                            candidate_response.url,
                        "athletics_domain":
                            get_domain(
                                candidate_response.url
                            ),
                        "discovery_method":
                            "page_link",
                        "attempts":
                            " | ".join(
                                attempts
                            ),
                    }

                time.sleep(
                    REQUEST_DELAY
                )

    return {
        "status": "not_found",
        "roster_url": "",
        "athletics_domain": "",
        "discovery_method": "",
        "attempts":
            " | ".join(
                attempts
            ),
    }


############################
# Main pipeline
############################


def main() -> None:
    """
    Discover roster URLs for all school-season
    combinations in the study.
    """

    schools_df = load_schools()

    ROSTER_SOURCES_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    session = requests.Session()

    records: list[dict] = []

    total_attempts = (
        len(schools_df)
        * len(SEASONS)
    )

    counter = 0

    for _, school in (
        schools_df.iterrows()
    ):
        school_name = school[
            "SCHOOL_NAME_OFFICIAL"
        ]

        for season in SEASONS:
            counter += 1

            print(
                "\n"
                f"[{counter}/"
                f"{total_attempts}] "
                f"{school_name} "
                f"({season})"
            )

            result = (
                discover_school_roster(
                    session,
                    school_name,
                    season,
                )
            )

            record = {
                "SCHOOL_NAME_OFFICIAL":
                    school_name,
                "DIVISION":
                    school[
                        "DIVISION"
                    ],
                "CONFERENCE_CODE":
                    school[
                        "CONFERENCE_CODE"
                    ],
                "PRIMARY_CONFERENCE":
                    school[
                        "PRIMARY_CONFERENCE"
                    ],
                "season":
                    season,
                **result,
            }

            records.append(
                record
            )

            # Save continuously so a long run
            # does not lose previous results.
            pd.DataFrame(
                records
            ).to_csv(
                ROSTER_SOURCES_FILE,
                index=False,
            )

            print(
                "    Result: "
                f"{result['status']}"
            )

            if result[
                "roster_url"
            ]:
                print(
                    "    URL: "
                    f"{result['roster_url']}"
                )

            time.sleep(
                REQUEST_DELAY
            )

    print(
        "\nDiscovery complete."
    )

    print(
        "Saved roster sources to:"
    )

    print(
        ROSTER_SOURCES_FILE
    )


if __name__ == "__main__":
    main()