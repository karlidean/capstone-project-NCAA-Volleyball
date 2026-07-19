"""
Collect NCAA women's volleyball roster data.

Input:
    data/interim/roster_sources.csv

Outputs:
    data/raw/rosters.csv
    outputs/collection_log.csv
"""

from __future__ import annotations

from datetime import (
    UTC,
    datetime,
)

import time
import traceback

import pandas as pd
import requests

from src.collectors import (
    extract_roster,
)

from src.collectors.browser import (
    fetch_rendered_page,
)

from src.collectors.visible_text import (
    extract_compact_text_roster,
)

from src.config import (
    COLLECTION_LOG_FILE,
    HEADERS,
    REQUEST_DELAY,
    REQUEST_TIMEOUT,
    ROSTERS_FILE,
    ROSTER_SOURCES_FILE,
)


############################
# Settings
############################

TEST_MODE = True

TEST_LIMIT = 10


############################
# Source loading
############################


def load_roster_sources(
) -> pd.DataFrame:
    """
    Load successfully discovered roster URLs.
    """

    sources_df = pd.read_csv(
        ROSTER_SOURCES_FILE
    )

    required_columns = {
        "SCHOOL_NAME_OFFICIAL",
        "DIVISION",
        "CONFERENCE_CODE",
        "PRIMARY_CONFERENCE",
        "season",
        "status",
        "roster_url",
    }

    missing_columns = (
        required_columns
        - set(
            sources_df.columns
        )
    )

    if missing_columns:
        raise ValueError(
            "roster_sources.csv is missing "
            "required columns: "
            + ", ".join(
                sorted(
                    missing_columns
                )
            )
        )

    sources_df = sources_df[
        sources_df[
            "status"
        ].astype(
            str
        ).str.lower()
        == "found"
    ].copy()

    sources_df = sources_df[
        sources_df[
            "roster_url"
        ].notna()
    ].copy()

    if TEST_MODE:
        sources_df = (
            sources_df.head(
                TEST_LIMIT
            )
        )

    return sources_df


############################
# Page fetching
############################


def fetch_static_html(
    url: str,
) -> str:
    """
    Fetch webpage HTML using requests.
    """

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
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
    season: int,
    source_url: str,
) -> pd.DataFrame:
    """
    Add school and collection metadata
    to roster records.
    """

    roster_df = (
        roster_df.copy()
    )

    roster_df[
        "school_name"
    ] = school_name

    roster_df[
        "division"
    ] = division

    roster_df[
        "conference_code"
    ] = conference_code

    roster_df[
        "primary_conference"
    ] = primary_conference

    roster_df[
        "season"
    ] = season

    roster_df[
        "source_url"
    ] = source_url

    roster_df[
        "collected_at"
    ] = datetime.now(
        UTC
    ).isoformat()

    return roster_df


############################
# One roster collection
############################


def collect_roster(
    source: pd.Series,
) -> tuple[
    pd.DataFrame,
    str,
    str,
]:
    """
    Collect and parse one roster URL.

    Returns:
        roster dataframe,
        parser used,
        fetch method
    """

    url = source[
        "roster_url"
    ]

    school_name = source[
        "SCHOOL_NAME_OFFICIAL"
    ]

    season = int(
        source["season"]
    )

    print(
        "\nCollecting "
        f"{school_name} "
        f"({season})"
    )

    print(
        url
    )

    ########################
    # Attempt 1:
    # Static requests HTML
    ########################

    static_error = None

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

        except ValueError as error:
            static_error = error
            raise

    except Exception as error:
        static_error = error

        print(
            "Static collection "
            "did not produce a usable "
            "roster. Trying Playwright."
        )

        ########################
        # Attempt 2:
        # Rendered browser page
        ########################

        rendered_page = (
            fetch_rendered_page(
                url
            )
        )

        ########################
        # Attempt 2a:
        # Visible text parser
        ########################

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

        except ValueError as text_error:

            ####################
            # Attempt 2b:
            # Rendered HTML
            ####################

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

            except ValueError as (
                rendered_error
            ):
                raise ValueError(
                    "All roster parsing "
                    "methods failed. "
                    f"Static: "
                    f"{static_error} | "
                    f"Visible text: "
                    f"{text_error} | "
                    f"Rendered HTML: "
                    f"{rendered_error}"
                ) from rendered_error

    print(
        f"Extracted "
        f"{len(roster_df)} "
        f"players using "
        f"{parser_used} "
        f"via {fetch_method}."
    )

    roster_df = add_metadata(
        roster_df,
        school_name=school_name,
        division=source[
            "DIVISION"
        ],
        conference_code=source[
            "CONFERENCE_CODE"
        ],
        primary_conference=source[
            "PRIMARY_CONFERENCE"
        ],
        season=season,
        source_url=url,
    )

    return (
        roster_df,
        parser_used,
        fetch_method,
    )


############################
# Save outputs
############################


def save_rosters(
    rosters: list[
        pd.DataFrame
    ],
) -> None:
    """
    Save successfully parsed rosters.
    """

    nonempty = [
        roster
        for roster in rosters
        if not roster.empty
    ]

    if not nonempty:
        print(
            "\nNo roster records "
            "were collected."
        )
        return

    combined_df = pd.concat(
        nonempty,
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
    """
    Save collection successes
    and failures.
    """

    COLLECTION_LOG_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    pd.DataFrame(
        records
    ).to_csv(
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
# Main
############################


def main() -> None:
    """
    Run roster collection pipeline.
    """

    sources_df = (
        load_roster_sources()
    )

    print(
        "Roster URLs loaded: "
        f"{len(sources_df)}"
    )

    if TEST_MODE:
        print(
            "Running in TEST_MODE "
            f"with first "
            f"{TEST_LIMIT} URLs."
        )

    collected_rosters: list[
        pd.DataFrame
    ] = []

    log_records: list[
        dict
    ] = []

    for _, source in (
        sources_df.iterrows()
    ):
        school_name = source[
            "SCHOOL_NAME_OFFICIAL"
        ]

        season = int(
            source["season"]
        )

        url = source[
            "roster_url"
        ]

        try:
            (
                roster_df,
                parser_used,
                fetch_method,
            ) = collect_roster(
                source
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
                    "season":
                        season,
                    "source_url":
                        url,
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

        except Exception as error:
            print(
                "\nFailed: "
                f"{school_name} "
                f"({season})"
            )

            print(
                error
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
                    "season":
                        season,
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

        time.sleep(
            REQUEST_DELAY
        )

    save_rosters(
        collected_rosters
    )

    save_collection_log(
        log_records
    )


if __name__ == "__main__":
    main()