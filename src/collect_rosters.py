"""
collect_rosters.py

This script is responsible for collecting NCAA volleyball rosters from
university athletics websites.
"""

########################
# Imports
########################

from datetime import datetime, UTC
from io import StringIO
import time

import pandas as pd
import requests
import traceback

from src.config import (
    COLLECTION_LOG_FILE,
    HEADERS,
    REQUEST_DELAY,
    ROSTERS_FILE,
    SCHOOLS_FILE,
    START_YEAR,
    END_YEAR,
)

def load_schools() -> pd.DataFrame:
    """
    Load the schools data from the CSV file.

    Returns:
        pd.DataFrame: DataFrame containing schools data.
    """
    schools_df = pd.read_csv(SCHOOLS_FILE)
    active_values =(
        schools_df["active"]
        .astype(str)
        .str.lower()
        .str.strip()
    )
    return schools_df[active_values == "true"].copy()

def build_roster_url(template: str, season: int) -> str:
    """ Insert the season into a school's roster URL template"""
    
    return template.format(season=season)

def fetch_roster_page(url: str) -> str:
    """Download a roster webpage and return its HTML"""

    response = requests.get(
        url,
        headers = HEADERS,
        timeout = 30,
    )

    response.raise_for_status()

    return response.text

def extract_roster_table(html: str) -> pd.DataFrame:
    """Extract the player roster table from the athletics webpage."""

    tables = pd.read_html(StringIO(html))

    for index, table in enumerate(tables):
        # Flatten columns in case pandas reads them as a MultiIndex.
        if isinstance(table.columns, pd.MultiIndex):
            table.columns = [
                " ".join(
                    str(part).strip()
                    for part in column
                    if str(part).strip() != "nan"
                )
                for column in table.columns
            ]

        normalized_columns = {
            str(column).strip().lower()
            for column in table.columns
        }

        print(f"Table {index} columns: {list(table.columns)}")

        if {"name", "pos.", "ht.", "yr.", "hometown"}.issubset(
            normalized_columns
        ):
            print(f"Roster table found at table index {index}")
            return table.copy()

    raise ValueError("No recognizable roster table was found.")

def standardize_columns(roster_df: pd.DataFrame) -> pd.DataFrame:
    """Standardize roster columns into the project schema."""

    # Normalize everything before mapping.
    roster_df.columns = [
        str(column).strip().lower()
        for column in roster_df.columns
    ]

    column_mapping = {
        "#": "jersey_number",
        "no.": "jersey_number",
        "number": "jersey_number",
        "name": "player_name",
        "pos.": "position",
        "pos": "position",
        "position": "position",
        "ht.": "height",
        "ht": "height",
        "height": "height",
        "yr.": "class_year",
        "yr": "class_year",
        "year": "class_year",
        "class": "class_year",
        "hometown": "hometown",
        "high school": "high_school",
        "previous school": "previous_school",
    }

    roster_df = roster_df.rename(columns=column_mapping)

    desired_columns = [
        "jersey_number",
        "player_name",
        "position",
        "height",
        "class_year",
        "hometown",
        "high_school",
        "previous_school",
    ]

    for column in desired_columns:
        if column not in roster_df.columns:
            roster_df[column] = pd.NA

    roster_df = roster_df[desired_columns].copy()

    # Remove accidental blank rows.
    roster_df = roster_df[
        roster_df["player_name"].notna()
        & (
            roster_df["player_name"]
            .astype(str)
            .str.strip()
            .ne("")
        )
    ].copy()

    return roster_df

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
    """Add metadata columns to the roster DataFrame"""

    roster_df["school_name"] = school_name
    roster_df["school_code"] = school_code
    roster_df["division"] = division
    roster_df["conference"] = conference
    roster_df["season"] = season
    roster_df["source_url"] = source_url
    roster_df["collected_at"] = collected_at = datetime.now(UTC).isoformat()

    return roster_df

def collect_school_season(
        school:pd.Series,
        season:int,
) -> pd.DataFrame:
    """Collect the roster for a specific school and season"""

    url = build_roster_url(school["roster_url_template"], season)

    try:
        html = fetch_roster_page(url)
        roster_df = extract_roster_table(html)
        roster_df = standardize_columns(roster_df)
        roster_df = add_metadata(
            roster_df,
            school_name=school["school_name"],
            school_code=school["school_code"],
            division=school["division"],
            conference=school["conference"],
            season=season,
            source_url=url,
        )
        return roster_df
    
    except Exception as e:
        print(f"Error collecting roster for {school['school_name']} ({season}): {e}")
        traceback.print_exc()
        return pd.DataFrame()  # Return an empty DataFrame on error
    
def save_rosters(rosters: list[pd.DataFrame]) -> None:
    """Save the collected rosters to a CSV file"""

    if not rosters:
        print("No rosters collected. Nothing to save.")
        return
    
    combined_df = pd.concat(rosters, ignore_index=True)

    ROSTERS_FILE.parent.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
    
    combined_df.to_csv(ROSTERS_FILE, index=False)
    
    print(f"Saved {len(combined_df)} roster records to {ROSTERS_FILE}")

def save_collection_log(log_records: list[dict]) -> None:
    """Save the collection log to a CSV file"""

    if not log_records:
        print("No log entries to save.")
        return
    
    COLLECTION_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)  
    # Ensure the directory exists
    
    log_df = pd.DataFrame(log_records)
    
    log_df.to_csv(COLLECTION_LOG_FILE, index=False)

    print(f"Saved collection log with {len(log_df)} entries to {COLLECTION_LOG_FILE}")

def main() -> None:
    """Collect roster data for all active schools and seasons."""

    schools_df = load_schools()
    collected_rosters: list[pd.DataFrame] = []
    log_records: list[dict] = []

    for _, school in schools_df.iterrows():
        for season in [2024]:
            url = build_roster_url(school["roster_url_template"], season)

        try:
            roster_df = collect_school_season(school, season)
            collected_rosters.append(roster_df)
            log_records.append({
                "school_name": school["school_name"],
                "school_code": school["school_code"],
                "season": season,
                "status": "success",
                "record_count": len(roster_df),
                "error": "",
            })
        
        except Exception as error:
            print(
                f"Failed: {school['school_name']} ({season}) - {error}"
            )
            log_records.append({
                "school_name": school["school_name"],
                "school_code": school["school_code"],
                "season": season,
                "status": "failed",
                "record_count": 0,
                "error": str(error),
            })
            time.sleep(REQUEST_DELAY)  # Delay to avoid rate limiting

    save_rosters(collected_rosters)
    save_collection_log(log_records)

if __name__ == "__main__":
    main()