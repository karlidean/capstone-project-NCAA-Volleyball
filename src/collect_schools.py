"""
collect_schools.py

This script's job is to collect NCAA volleyball schools out of their
conferences for further analysis.
"""

import re

import pandas as pd

from src.config import SCHOOLS_FILE


CONFERENCE_SCHOOLS: dict[str, list[str]] = {
    "B1G": [
        "Illinois",
        "Indiana",
        "Iowa",
        "Maryland",
        "Michigan",
        "Michigan State",
        "Minnesota",
        "Nebraska",
        "Northwestern",
        "Ohio State",
        "Oregon",
        "Penn State",
        "Purdue",
        "Rutgers",
        "UCLA",
        "USC",
        "Washington",
        "Wisconsin",
    ],
    "ACC": [
        "Boston College",
        "California",
        "Clemson",
        "Duke",
        "Florida State",
        "Georgia Tech",
        "Louisville",
        "Miami",
        "North Carolina",
        "NC State",
        "Notre Dame",
        "Pittsburgh",
        "SMU",
        "Stanford",
        "Syracuse",
        "Virginia",
        "Virginia Tech",
        "Wake Forest",
    ],
    "B12": [
        "Arizona",
        "Arizona State",
        "Baylor",
        "BYU",
        "UCF",
        "Cincinnati",
        "Colorado",
        "Houston",
        "Iowa State",
        "Kansas",
        "Kansas State",
        "Oklahoma State",
        "TCU",
        "Texas Tech",
        "Utah",
        "West Virginia",
    ],
    "SEC": [
        "Alabama",
        "Arkansas",
        "Auburn",
        "Florida",
        "Georgia",
        "Kentucky",
        "LSU",
        "Mississippi State",
        "Missouri",
        "Oklahoma",
        "Ole Miss",
        "South Carolina",
        "Tennessee",
        "Texas",
        "Texas A&M",
        "Vanderbilt",
    ],
    "BE": [
        "Butler",
        "Connecticut",
        "Creighton",
        "DePaul",
        "Georgetown",
        "Marquette",
        "Providence",
        "St. John's",
        "Seton Hall",
        "Villanova",
        "Xavier",
    ],
    "MVC": [
        "Belmont",
        "Bradley",
        "Drake",
        "Evansville",
        "UIC",
        "Illinois State",
        "Indiana State",
        "Murray State",
        "Northern Iowa",
        "Southern Illinois",
        "Valparaiso",
    ],
    "A10": [
        "Davidson",
        "Dayton",
        "Duquesne",
        "Fordham",
        "George Mason",
        "George Washington",
        "La Salle",
        "Loyola Chicago",
        "Rhode Island",
        "Saint Louis",
        "St. Bonaventure",
        "VCU",
    ],
    "WCC": [
        "Denver",
        "Gonzaga",
        "Loyola Marymount",
        "Oregon State",
        "Pacific",
        "Pepperdine",
        "Portland",
        "Saint Mary's",
        "San Francisco",
        "Santa Clara",
    ],
}


def create_school_code(school_name: str) -> str:
    """Convert a school name into a stable lowercase identifier."""

    substitutions = {
        "Connecticut": "uconn",
        "Pittsburgh": "pitt",
        "Saint Louis": "slu",
        "St. John's": "st_johns",
        "St. Bonaventure": "st_bonaventure",
        "Saint Mary's": "saint_marys",
        "North Carolina": "unc",
        "NC State": "nc_state",
        "Southern California": "usc",
    }

    if school_name in substitutions:
        return substitutions[school_name]

    school_code = school_name.lower()
    school_code = school_code.replace("&", "and")
    school_code = re.sub(r"[^a-z0-9]+", "_", school_code)

    return school_code.strip("_")


def build_school_catalog() -> pd.DataFrame:
    """Build one catalog row for each school in each target conference."""

    records: list[dict] = []

    for conference_code, school_names in CONFERENCE_SCHOOLS.items():
        for school_name in school_names:
            records.append(
                {
                    "school_code": create_school_code(school_name),
                    "school_name": school_name,
                    "current_conference_code": conference_code,
                    "athletics_domain": pd.NA,
                    "roster_url_template": pd.NA,
                    "platform": "unknown",
                    "active": True,
                }
            )

    schools_df = pd.DataFrame(records)

    schools_df = schools_df.sort_values(
        by=["current_conference_code", "school_name"]
    ).reset_index(drop=True)

    return schools_df


def validate_school_catalog(schools_df: pd.DataFrame) -> None:
    """Raise an error when required school catalog values are invalid."""

    required_columns = {
        "school_code",
        "school_name",
        "current_conference_code",
        "athletics_domain",
        "roster_url_template",
        "platform",
        "active",
    }

    missing_columns = required_columns.difference(schools_df.columns)

    if missing_columns:
        raise ValueError(
            f"School catalog is missing columns: {sorted(missing_columns)}"
        )

    duplicated_codes = schools_df[
        schools_df["school_code"].duplicated(keep=False)
    ]

    if not duplicated_codes.empty:
        duplicate_values = sorted(
            duplicated_codes["school_code"].unique()
        )

        raise ValueError(
            f"Duplicate school codes found: {duplicate_values}"
        )

    if schools_df["school_name"].isna().any():
        raise ValueError("The catalog contains a missing school name.")


def save_school_catalog(schools_df: pd.DataFrame) -> None:
    """Save the school catalog to the raw data directory."""

    SCHOOLS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    schools_df.to_csv(
        SCHOOLS_FILE,
        index=False,
    )

    print(f"Saved {len(schools_df)} schools to:")
    print(SCHOOLS_FILE)

    print("\nSchools by current conference:")
    print(
        schools_df.groupby("current_conference_code")
        .size()
        .sort_index()
    )


def main() -> None:
    """Build, validate, and save the initial school catalog."""

    schools_df = build_school_catalog()
    validate_school_catalog(schools_df)
    save_school_catalog(schools_df)


if __name__ == "__main__":
    main()