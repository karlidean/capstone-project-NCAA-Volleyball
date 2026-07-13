"""
collect_rosters.py

Collect NCAA women's volleyball rosters from university athletics websites.
"""

########################
# Imports
########################

from datetime import UTC, datetime
import time
import traceback

import pandas as pd
import requests

from src.collectors.visible_text import (
    extract_compact_text_roster,
)
from src.collectors import extract_roster
from src.collectors.browser import fetch_rendered_page
from src.collectors.visible_text import extract_compact_text_roster
from src.config import (
    COLLECTION_LOG_FILE,
    HEADERS,
    REQUEST_DELAY,
    ROSTERS_FILE,
    SCHOOLS_FILE,
)


########################
# Test Settings
########################

TEST_MODE = True

TEST_SCHOOL_CODES = [
    "indiana",
    "iowa",
    "penn_state",
]

TEST_SEASONS = [2024]


########################
# School Loading
########################


def load_schools() -> pd.DataFrame:
    """Load active schools that have configured roster URLs."""

    schools_df = pd.read_csv(SCHOOLS_FILE)

    active_values = (
        schools_df["active"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    schools_df = schools_df[
        active_values == "true"
    ].copy()

    schools_df = schools_df[
        schools_df["roster_url_template"].notna()
        & (
            schools_df["roster_url_template"]
            .astype(str)
            .str.strip()
            .ne("")
        )
    ].copy()

    return schools_df


########################
# URL Construction
########################


def build_roster_url(
    template: str,
    season: int,
    season_format: str = "calendar_year",
) -> str:
    """Build a roster URL using the school's season format."""

    normalized_format = (
        str(season_format)
        .strip()
        .lower()
    )

    if normalized_format == "academic_year":
        next_year = str(season + 1)[-2:]
        season_url = f"{season}-{next_year}"
    else:
        season_url = str(season)

    return str(template).format(
        season=season,
        season_url=season_url,
    )


########################
# Page Collection
########################


def fetch_static_html(url: str) -> str:
    """Download a webpage using requests and return its HTML."""

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    return response.text


########################
# Metadata
########################


def add_metadata(
    roster_df: pd.DataFrame,
    *,
    school_name: str,
    school_code: str,
    division: str,
    conference: str,
    season: int,
    source_url: str,
) -> pd.DataFrame:
    """Add school, season, and source metadata to roster records."""

    roster_df = roster_df.copy()

    roster_df["school_name"] = school_name
    roster_df["school_code"] = school_code
    roster_df["division"] = division
    roster_df["conference"] = conference
    roster_df["season"] = season
    roster_df["source_url"] = source_url
    roster_df["collected_at"] = datetime.now(UTC).isoformat()

    return roster_df


########################
# Roster Collection
########################


def collect_school_season(
    school: pd.Series,
    season: int,
) -> tuple[pd.DataFrame, str, str, str]:
    """
    Collect one roster for one school and season.

    Returns:
        A tuple containing:
        - standardized roster DataFrame;
        - parser name;
        - source URL;
        - fetch method.
    """

    url = build_roster_url(
        school["roster_url_template"],
        season,
        school.get("season_format", "calendar_year"),
    )

    print(
        f"\nCollecting {school['school_name']} "
        f"({season}): {url}"
    )

    platform = school.get("platform", "unknown")

    # First attempt: fast static HTML request.
    static_html = fetch_static_html(url)

    try:
        roster_df, parser_used = extract_roster(
            static_html,
            platform=platform,
        )

        fetch_method = "requests"

    except ValueError as static_error:
        print(
            "Static HTML did not contain a usable roster. "
            "Retrying with Chromium..."
        )

        # This assignment must occur before rendered_page is used.
        rendered_page = fetch_rendered_page(url)

        for line in rendered_page.visible_text.splitlines():
            if "Madi Sell" in line:
                print("MADI LINE:", repr(line))

        debug_dir = ROSTERS_FILE.parent / "debug_text"

        debug_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        debug_path = (
            debug_dir
            / f"{school['school_code']}_{season}.txt"
        )

        debug_path.write_text(
            rendered_page.visible_text,
            encoding="utf-8",
        )

        print(f"Saved rendered text to: {debug_path}")

        # First try the visible-text parser.
        try:
            roster_df = extract_compact_text_roster(
                rendered_page.visible_text
            )

            parser_used = "compact_visible_text"
            fetch_method = "playwright"

        except ValueError as text_error:
            # If visible text fails, try the regular parsers
            # against the rendered HTML.
            try:
                roster_df, parser_used = extract_roster(
                    rendered_page.html,
                    platform=platform,
                )

                fetch_method = "playwright"

            except ValueError as rendered_html_error:
                raise ValueError(
                    "Roster parsing failed after all collection methods. "
                    f"Static HTML: {static_error} | "
                    f"Visible text: {text_error} | "
                    f"Rendered HTML: {rendered_html_error} | "
                    f"Rendered text saved to: {debug_path}"
                ) from rendered_html_error

    print(
        f"Extracted {len(roster_df)} players "
        f"using the {parser_used} parser "
        f"with {fetch_method}."
    )

    roster_df = add_metadata(
        roster_df,
        school_name=school["school_name"],
        school_code=school["school_code"],
        division=school.get("division", "DI"),
        conference=school.get(
            "current_conference_code",
            pd.NA,
        ),
        season=season,
        source_url=url,
    )

    return (
        roster_df,
        parser_used,
        url,
        fetch_method,
    )


########################
# File Saving
########################


def save_rosters(
    rosters: list[pd.DataFrame],
) -> None:
    """Combine and save successfully collected rosters."""

    nonempty_rosters = [
        roster_df
        for roster_df in rosters
        if not roster_df.empty
    ]

    if not nonempty_rosters:
        print("\nNo roster records were collected.")
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
        f"\nSaved {len(combined_df)} roster records to:"
    )
    print(ROSTERS_FILE)


def save_collection_log(
    log_records: list[dict],
) -> None:
    """Save collection successes and failures."""

    if not log_records:
        print("No collection-log entries were generated.")
        return

    COLLECTION_LOG_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    log_df = pd.DataFrame(log_records)

    log_df.to_csv(
        COLLECTION_LOG_FILE,
        index=False,
    )

    print(
        f"Saved {len(log_df)} collection-log entries to:"
    )
    print(COLLECTION_LOG_FILE)


########################
# Main Pipeline
########################


def main() -> None:
    """Collect roster data for configured schools and seasons."""

    schools_df = load_schools()

    if TEST_MODE:
        schools_df = schools_df[
            schools_df["school_code"].isin(
                TEST_SCHOOL_CODES
            )
        ].copy()

        seasons = TEST_SEASONS

        print(
            "Running in test mode for schools: "
            f"{TEST_SCHOOL_CODES}"
        )

    else:
        seasons = list(
            range(2018, 2027)
        )

    print(
        f"Configured active schools loaded: "
        f"{len(schools_df)}"
    )

    collected_rosters: list[pd.DataFrame] = []
    log_records: list[dict] = []

    for _, school in schools_df.iterrows():
        for season in seasons:
            url = build_roster_url(
                school["roster_url_template"],
                season,
                school.get(
                    "season_format",
                    "calendar_year",
                ),
            )

            try:
                (
                    roster_df,
                    parser_used,
                    url,
                    fetch_method,
                ) = collect_school_season(
                    school,
                    season,
                )

                collected_rosters.append(
                    roster_df
                )

                log_records.append(
                    {
                        "school_name": school["school_name"],
                        "school_code": school["school_code"],
                        "season": season,
                        "source_url": url,
                        "status": "success",
                        "record_count": len(roster_df),
                        "parser_used": parser_used,
                        "error": "",
                        "fetch_method": fetch_method,
                    }
                )

            except Exception as error:
                print(
                    f"Failed: {school['school_name']} "
                    f"({season}): {error}"
                )

                traceback.print_exc()

                log_records.append(
                    {
                        "school_name": school["school_name"],
                        "school_code": school["school_code"],
                        "season": season,
                        "source_url": url,
                        "status": "failed",
                        "record_count": 0,
                        "parser_used": "",
                        "error": (
                            f"{type(error).__name__}: "
                            f"{error}"
                        ),
                        "fetch_method": "",
                    }
                )

            time.sleep(REQUEST_DELAY)

    save_rosters(collected_rosters)
    save_collection_log(log_records)


if __name__ == "__main__":
    main()