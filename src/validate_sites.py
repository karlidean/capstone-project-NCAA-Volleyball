from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.config import (
    HEADERS,
    REQUEST_DELAY,
    REQUEST_TIMEOUT,
    RAW_DATA_DIR,
    INTERIM_DATA_DIR,
)


INPUT_FILE = RAW_DATA_DIR / "school_list.csv"
OUTPUT_FILE = INTERIM_DATA_DIR / "validated_school_sites.csv"


def normalize_url(url: str) -> str:
    """Clean basic whitespace and normalize missing schemes."""

    url = str(url).strip()

    if not url:
        return ""

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    return url


def get_domain(url: str) -> str:
    """Return a normalized hostname."""

    try:
        domain = urlparse(url).netloc.lower()
    except ValueError:
        return ""

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


def fetch_url(
    session: requests.Session,
    url: str,
) -> tuple[requests.Response | None, str]:
    """
    Fetch a URL and return the response plus an error message.
    """

    try:
        response = session.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )

        return response, ""

    except requests.RequestException as error:
        return None, f"{type(error).__name__}: {error}"


def page_text(response: requests.Response) -> tuple[str, str]:
    """
    Return page title and visible text as lowercase strings.
    """

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    title = (
        soup.title.get_text(" ", strip=True).lower()
        if soup.title
        else ""
    )

    text = soup.get_text(
        " ",
        strip=True,
    ).lower()

    return title, text


def looks_like_volleyball_page(
    response: requests.Response,
) -> bool:
    """Check whether the page appears related to volleyball."""

    title, text = page_text(response)

    combined = f"{title} {text}"

    volleyball_terms = [
        "women's volleyball",
        "womens volleyball",
        "volleyball",
    ]

    return any(
        term in combined
        for term in volleyball_terms
    )


def looks_like_roster_page(
    response: requests.Response,
) -> bool:
    """Check whether the page appears to be a roster."""

    title, text = page_text(response)

    url = response.url.lower()

    roster_signal = (
        "roster" in title
        or "roster" in text
        or "/roster" in url
    )

    player_fields = [
        "height",
        "position",
        "hometown",
        "class",
        "year",
        "jersey",
    ]

    player_signal_count = sum(
        field in text
        for field in player_fields
    )

    return (
        roster_signal
        and player_signal_count >= 2
    )


def classify_page(
    response: requests.Response | None,
    error: str,
) -> tuple[str, bool, bool]:
    """
    Classify the result of a URL validation attempt.

    Returns:
        validation_status,
        is_volleyball_page,
        is_roster_page
    """

    if response is None:
        return "request_failed", False, False

    if response.status_code >= 400:
        return "http_error", False, False

    volleyball = looks_like_volleyball_page(
        response
    )

    roster = (
        looks_like_roster_page(response)
        if volleyball
        else False
    )

    if roster:
        return "valid_roster", True, True

    if volleyball:
        return "volleyball_not_roster", True, False

    return "not_volleyball", False, False


def main() -> None:
    """Validate every candidate SITE URL."""

    schools_df = pd.read_csv(
        INPUT_FILE
    )

    # Clean column names in case Excel added spaces or BOM characters.
    schools_df.columns = (
        schools_df.columns
        .astype(str)
        .str.strip()
        .str.replace("\ufeff", "", regex=False)

    )

    print("Columns found:")
    print(schools_df.columns.tolist())

    required_columns = {
        "CONFERENCE_CODE",
        "DIVISION",
        "PRIMARY_CONFERENCE",
        "SCHOOL_NAME_OFFICIAL",
        "SITE",
    }

    missing_columns = (
        required_columns
        - set(schools_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(sorted(missing_columns))
            + "\nColumns actually found: "
            + ", ".join(schools_df.columns)
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    session = requests.Session()

    records: list[dict] = []

    total = len(schools_df)

    for index, (_, school) in enumerate(
        schools_df.iterrows(),
        start=1,
    ):
        school_name = str(
            school["SCHOOL_NAME_OFFICIAL"]
        ).strip()

        candidate_url = normalize_url(
            school["SITE"]
        )

        print(
            f"\n[{index}/{total}] "
            f"{school_name}"
        )

        print(
            f"  Candidate: "
            f"{candidate_url or 'MISSING'}"
        )

        if not candidate_url:
            record = {
                **school.to_dict(),
                "HTTP_STATUS": "",
                "FINAL_URL": "",
                "CANDIDATE_DOMAIN": "",
                "FINAL_DOMAIN": "",
                "IS_VOLLEYBALL_PAGE": False,
                "IS_ROSTER_PAGE": False,
                "VALIDATION_STATUS": "missing_url",
                "ERROR": "",
            }

            records.append(record)

            pd.DataFrame(
                records
            ).to_csv(
                OUTPUT_FILE,
                index=False,
            )

            continue

        response, error = fetch_url(
            session,
            candidate_url,
        )

        validation_status, is_volleyball, is_roster = (
            classify_page(
                response,
                error,
            )
        )

        if response is not None:
            http_status = response.status_code
            final_url = response.url
        else:
            http_status = ""
            final_url = ""

        candidate_domain = get_domain(
            candidate_url
        )

        final_domain = get_domain(
            final_url
        )

        print(
            f"  Status: "
            f"{validation_status}"
        )

        if final_url:
            print(
                f"  Final URL: "
                f"{final_url}"
            )

        record = {
            **school.to_dict(),
            "HTTP_STATUS": http_status,
            "FINAL_URL": final_url,
            "CANDIDATE_DOMAIN": candidate_domain,
            "FINAL_DOMAIN": final_domain,
            "IS_VOLLEYBALL_PAGE": is_volleyball,
            "IS_ROSTER_PAGE": is_roster,
            "VALIDATION_STATUS": validation_status,
            "ERROR": error,
        }

        records.append(
            record
        )

        # Save after every row so progress is preserved.
        pd.DataFrame(
            records
        ).to_csv(
            OUTPUT_FILE,
            index=False,
        )

        time.sleep(
            REQUEST_DELAY
        )

    print(
        "\nValidation complete."
    )

    print(
        f"Saved results to: "
        f"{OUTPUT_FILE}"
    )

    results_df = pd.DataFrame(
        records
    )

    print(
        "\nValidation summary:"
    )

    print(
        results_df[
            "VALIDATION_STATUS"
        ].value_counts(
            dropna=False
        )
    )


if __name__ == "__main__":
    main()