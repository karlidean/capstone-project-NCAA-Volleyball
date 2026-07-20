"""
Collect NCAA women's volleyball roster data directly from curated roster URLs.

Input:
    data/raw/school_list.csv

Required columns:
    CONFERENCE_CODE
    DIVISION
    PRIMARY_CONFERENCE
    SCHOOL_NAME_OFFICIAL
    SITE

Outputs:
    data/raw/rosters.csv
    outputs/collection_log.csv
"""

from __future__ import annotations

from datetime import UTC, datetime
import time
import traceback

import pandas as pd
import requests

from src.collectors import extract_roster
from src.collectors.browser import fetch_rendered_page
from src.collectors.visible_text import extract_compact_text_roster

from src.config import (
    COLLECTION_LOG_FILE,
    HEADERS,
    REQUEST_DELAY,
    REQUEST_TIMEOUT,
    ROSTERS_FILE,
    SCHOOL_LIST_FILE,
)


############################
# Test settings
############################

TEST_MODE = False
TEST_LIMIT = 20


############################
# Load roster sources
############################


def load_roster_sources() -> pd.DataFrame:
    """Load schools with curated roster URLs."""

    schools_df = pd.read_csv(
        SCHOOL_LIST_FILE,
        encoding="utf-8-sig",
    )

    # Clean Excel/CSV column-name weirdness.
    schools_df.columns = (
        schools_df.columns
        .astype(str)
        .str.strip()
        .str.replace("\ufeff", "", regex=False)
    )

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
            "school_list.csv is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    # Keep only rows with a URL.
    schools_df = schools_df[
        schools_df["SITE"].notna()
    ].copy()

    schools_df["SITE"] = (
        schools_df["SITE"]
        .astype(str)
        .str.strip()
    )

    schools_df = schools_df[
        schools_df["SITE"].ne("")
    ].copy()

    if TEST_MODE:
        schools_df = schools_df.head(
            TEST_LIMIT
        )

    return schools_df


############################
# Page fetching
############################


def fetch_static_html(
    url: str,
) -> str:
    """Fetch roster page with requests."""

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
        allow_redirects=True,
    )

    response.raise_for_status()

    return response.text


############################
# Metadata
############################


def add_metadata(
    roster_df: pd.DataFrame,
    *,
    school_name: str,
    division: str,
    conference_code: str,
    primary_conference: str,
    source_url: str,
) -> pd.DataFrame:
    """Add school and collection metadata."""

    roster_df = roster_df.copy()

    roster_df["school_name"] = (
        school_name
    )

    roster_df["division"] = (
        division
    )

    roster_df["conference_code"] = (
        conference_code
    )

    roster_df["primary_conference"] = (
        primary_conference
    )

    roster_df["source_url"] = (
        source_url
    )

    roster_df["collected_at"] = (
        datetime.now(
            UTC
        ).isoformat()
    )

    return roster_df


############################
# Collect one roster
############################


def collect_roster(
    source: pd.Series,
) -> tuple[
    pd.DataFrame,
    str,
    str,
    str,
]:
    """
    Collect and parse one roster.

    Returns:
        roster DataFrame,
        parser used,
        fetch method,
        final source URL
    """

    school_name = str(
        source[
            "SCHOOL_NAME_OFFICIAL"
        ]
    ).strip()

    url = str(
        source["SITE"]
    ).strip()

    print(
        "\n"
        f"Collecting: {school_name}"
    )

    print(
        f"URL: {url}"
    )

    static_error = None

    ############################
    # Attempt 1: requests
    ############################

    try:
        static_html = (
            fetch_static_html(
                url
            )
        )

        try:
            (
                roster_df,
                parser_used,
            ) = extract_roster(
                static_html,
                platform="unknown",
            )

            fetch_method = (
                "requests"
            )

            return (
                roster_df,
                parser_used,
                fetch_method,
                url,
            )

        except ValueError as error:
            static_error = error

    except Exception as error:
        static_error = error

    print(
        "Static HTML did not produce "
        "a usable roster."
    )

    print(
        "Trying Playwright..."
    )

    ############################
    # Attempt 2: Playwright
    ############################

    rendered_page = (
        fetch_rendered_page(
            url
        )
    )

    ############################
    # Attempt 2A:
    # Visible-text parser
    ############################

    try:
        roster_df = (
            extract_compact_text_roster(
                rendered_page.visible_text
            )
        )

        parser_used = (
            "compact_visible_text"
        )

        fetch_method = (
            "playwright_visible_text"
        )

        return (
            roster_df,
            parser_used,
            fetch_method,
            url,
        )

    except ValueError as text_error:

        ########################
        # Attempt 2B:
        # Rendered HTML parsers
        ########################

        try:
            (
                roster_df,
                parser_used,
            ) = extract_roster(
                rendered_page.html,
                platform="unknown",
            )

            fetch_method = (
                "playwright_html"
            )

            return (
                roster_df,
                parser_used,
                fetch_method,
                url,
            )

        except ValueError as rendered_error:
            raise ValueError(
                "All roster parsing methods failed. "
                f"Static: {static_error} | "
                f"Visible text: {text_error} | "
                f"Rendered HTML: {rendered_error}"
            ) from rendered_error


############################
# Save results
############################


def save_rosters(
    rosters: list[
        pd.DataFrame
    ],
) -> None:
    """Save successfully collected rosters."""

    nonempty_rosters = [
        roster
        for roster in rosters
        if not roster.empty
    ]

    if not nonempty_rosters:
        print(
            "\nNo roster records "
            "were collected."
        )
        return

    combined_df = pd.concat(
        nonempty_rosters,
        ignore_index=True,
    )

    ROSTERS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    combined_df.to_csv(
        ROSTERS_FILE,
        index=False,
    )

    print(
        "\nSaved "
        f"{len(combined_df)} "
        "roster records to:"
    )

    print(
        ROSTERS_FILE
    )


def save_collection_log(
    records: list[dict],
) -> None:
    """Save collection successes and failures."""

    COLLECTION_LOG_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    log_df = pd.DataFrame(
        records
    )

    log_df.to_csv(
        COLLECTION_LOG_FILE,
        index=False,
    )

    print(
        "\nSaved collection log to:"
    )

    print(
        COLLECTION_LOG_FILE
    )


############################
# Main pipeline
############################


def main() -> None:
    """Run roster collection."""

    sources_df = (
        load_roster_sources()
    )

    print(
        "\nRoster URLs loaded: "
        f"{len(sources_df)}"
    )

    if TEST_MODE:
        print(
            "TEST MODE enabled. "
            f"Testing first {TEST_LIMIT} URLs."
        )

    collected_rosters: list[
        pd.DataFrame
    ] = []

    log_records: list[
        dict
    ] = []

    total = len(
        sources_df
    )

    for index, (
        _,
        source,
    ) in enumerate(
        sources_df.iterrows(),
        start=1,
    ):
        school_name = str(
            source[
                "SCHOOL_NAME_OFFICIAL"
            ]
        ).strip()

        url = str(
            source["SITE"]
        ).strip()

        print(
            "\n"
            f"[{index}/{total}]"
        )

        try:
            (
                roster_df,
                parser_used,
                fetch_method,
                final_url,
            ) = collect_roster(
                source
            )

            roster_df = add_metadata(
                roster_df,
                school_name=school_name,
                division=str(
                    source["DIVISION"]
                ),
                conference_code=str(
                    source[
                        "CONFERENCE_CODE"
                    ]
                ),
                primary_conference=str(
                    source[
                        "PRIMARY_CONFERENCE"
                    ]
                ),
                source_url=final_url,
            )

            collected_rosters.append(
                roster_df
            )

            log_records.append(
                {
                    "school_name":
                        school_name,
                    "division":
                        source[
                            "DIVISION"
                        ],
                    "conference_code":
                        source[
                            "CONFERENCE_CODE"
                        ],
                    "source_url":
                        final_url,
                    "status":
                        "success",
                    "record_count":
                        len(
                            roster_df
                        ),
                    "parser_used":
                        parser_used,
                    "fetch_method":
                        fetch_method,
                    "error":
                        "",
                }
            )

            print(
                "SUCCESS: "
                f"{len(roster_df)} "
                "players | "
                f"{parser_used} | "
                f"{fetch_method}"
            )

        except Exception as error:
            print(
                "\nFAILED: "
                f"{school_name}"
            )

            print(
                f"{type(error).__name__}: "
                f"{error}"
            )

            traceback.print_exc()

            log_records.append(
                {
                    "school_name":
                        school_name,
                    "division":
                        source[
                            "DIVISION"
                        ],
                    "conference_code":
                        source[
                            "CONFERENCE_CODE"
                        ],
                    "source_url":
                        url,
                    "status":
                        "failed",
                    "record_count":
                        0,
                    "parser_used":
                        "",
                    "fetch_method":
                        "",
                    "error":
                        (
                            f"{type(error).__name__}: "
                            f"{error}"
                        ),
                }
            )

        # Save progress after every school.
        save_collection_log(
            log_records
        )

        time.sleep(
            REQUEST_DELAY
        )

    save_rosters(
        collected_rosters
    )

    save_collection_log(
        log_records
    )

    print(
        "\nCollection complete."
    )


if __name__ == "__main__":
    main()