from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Iterable

import requests
from bs4 import BeautifulSoup

INPUT_FILE = Path("data/raw/school_list.csv")
OUTPUT_FILE = Path("outputs/discovered_roster_urls.csv")

REQUEST_TIMEOUT = 20
REQUEST_DELAY = 1.0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    )
}

URL_PATTERNS = [
    "https://{domain}/sports/womens-volleyball/roster/{season}",
    "https://{domain}/sports/womens-volleyball/roster/season/{season}",
    "https://{domain}/sports/womens-volleyball/roster/season/{season_url}",
    "https://{domain}/sports/wvball/roster/{season}",
    "https://{domain}/sports/wvball/roster/season/{season}",
    "https://{domain}/sports/wvball/roster/season/{season_url}",
    "https://{domain}/sports/volleyball/roster/{season}",
    "https://{domain}/sports/volleyball/roster/season/{season}",
    "https://{domain}/sports/volleyball/roster/season/{season_url}",
]


def season_to_academic_year(season: int) -> str:
    return f"{season}-{str(season + 1)[-2:]}"


def load_schools(path: Path) -> list[dict[str, str]]:
    """Load schools from the NCAA population file."""

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        required_columns = {
            "CONFERENCE_CODE",
            "DIVISION",
            "PRIMARY_CONFERENCE",
            "SCHOOL_NAME_OFFICIAL",
        }

        if not reader.fieldnames:
            raise ValueError("The input CSV has no header row.")

        missing_columns = required_columns - set(reader.fieldnames)

        if missing_columns:
            raise ValueError(
                "Missing required columns: "
                + ", ".join(sorted(missing_columns))
            )

        schools = []

        for row in reader:
            school_name = row.get(
                "SCHOOL_NAME_OFFICIAL",
                "",
            ).strip()

            if not school_name:
                continue

            schools.append(row)

    return schools


def normalize_domain(domain: str) -> str:
    domain = domain.strip().rstrip("/")

    if domain.startswith("https://"):
        domain = domain.removeprefix("https://")

    if domain.startswith("http://"):
        domain = domain.removeprefix("http://")

    return domain


def generate_candidate_urls(
    domain: str,
    season: int,
) -> Iterable[tuple[str, str]]:
    domain = normalize_domain(domain)
    season_url = season_to_academic_year(season)

    for pattern in URL_PATTERNS:
        url = pattern.format(
            domain=domain,
            season=season,
            season_url=season_url,
        )

        if "{season_url}" in pattern:
            season_format = "academic_year"
        else:
            season_format = "calendar_year"

        yield url, season_format


def looks_like_roster_page(
    response: requests.Response,
) -> bool:
    """Check whether a page appears to be a volleyball roster."""

    if response.status_code != 200:
        return False

    if not response.text:
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

    text = soup.get_text(
        " ",
        strip=True,
    ).lower()

    error_terms = [
        "page not found",
        "404",
        "access denied",
    ]

    if any(
        term in title
        for term in error_terms
    ):
        return False

    roster_signals = [
        "roster",
        "women's volleyball",
        "womens volleyball",
        "volleyball roster",
    ]

    player_signals = [
        "position",
        "height",
        "hometown",
        "class",
        "year",
        "jersey",
    ]

    roster_signal_count = sum(
        signal in title or signal in text
        for signal in roster_signals
    )

    player_signal_count = sum(
        signal in text
        for signal in player_signals
    )

    return (
        roster_signal_count >= 1
        and player_signal_count >= 2
    )


def discover_roster_url(
    session: requests.Session,
    domain: str,
    season: int,
) -> dict[str, str]:
    """Try common roster URL patterns."""

    attempts = []

    for (
        url,
        season_format,
    ) in generate_candidate_urls(
        domain,
        season,
    ):
        try:
            response = session.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )

            attempts.append(
                f"{response.status_code}:"
                f"{response.url}"
            )

            if looks_like_roster_page(
                response
            ):
                return {
                    "status": "found",
                    "roster_url": response.url,
                    "season_format": season_format,
                    "http_status": str(
                        response.status_code
                    ),
                    "attempts": " | ".join(
                        attempts
                    ),
                }

        except requests.RequestException as exc:
            attempts.append(
                f"ERROR:{url}:"
                f"{type(exc).__name__}"
            )

        time.sleep(REQUEST_DELAY)

    return {
        "status": "not_found",
        "roster_url": "",
        "season_format": "",
        "http_status": "",
        "attempts": " | ".join(
            attempts
        ),
    }


def get_domain_from_row(
    school: dict[str, str],
) -> str:
    """
    Read a domain if one exists.

    This supports either ATHLETICS_DOMAIN or domain
    so the script remains flexible.
    """

    return (
        school.get(
            "ATHLETICS_DOMAIN",
            "",
        ).strip()
        or school.get(
            "domain",
            "",
        ).strip()
    )


def main(
    season: int = 2024,
) -> None:
    schools = load_schools(
        INPUT_FILE
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "SCHOOL_NAME_OFFICIAL",
        "DIVISION",
        "CONFERENCE_CODE",
        "PRIMARY_CONFERENCE",
        "season",
        "athletics_domain",
        "status",
        "roster_url",
        "season_format",
        "http_status",
        "attempts",
    ]

    session = requests.Session()

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for (
            index,
            school,
        ) in enumerate(
            schools,
            start=1,
        ):
            school_name = school[
                "SCHOOL_NAME_OFFICIAL"
            ]

            division = school.get(
                "DIVISION",
                "",
            )

            conference_code = (
                school.get(
                    "CONFERENCE_CODE",
                    "",
                )
            )

            primary_conference = (
                school.get(
                    "PRIMARY_CONFERENCE",
                    "",
                )
            )

            domain = get_domain_from_row(
                school
            )

            print(
                f"[{index}/{len(schools)}] "
                f"{school_name} "
                f"({division}, "
                f"{conference_code})"
            )

            if not domain:
                result = {
                    "status": "missing_domain",
                    "roster_url": "",
                    "season_format": "",
                    "http_status": "",
                    "attempts": "",
                }

                print(
                    "  -> No athletics "
                    "domain available."
                )

            else:
                result = (
                    discover_roster_url(
                        session=session,
                        domain=domain,
                        season=season,
                    )
                )

                print(
                    f"  -> "
                    f"{result['status']}: "
                    f"{result['roster_url']}: "
                    f"or 'No URL found'"
                )

            writer.writerow(
                {
                    "SCHOOL_NAME_OFFICIAL":
                        school_name,
                    "DIVISION":
                        division,
                    "CONFERENCE_CODE":
                        conference_code,
                    "PRIMARY_CONFERENCE":
                        primary_conference,
                    "season":
                        season,
                    "athletics_domain":
                        domain,
                    **result,
                }
            )

            output_file.flush()


if __name__ == "__main__":
    main(
        season=2024
    )