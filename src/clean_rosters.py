"""Clean and standardize NCAA women's volleyball roster data.

Input:
    data/processed/rosters_geographic.csv

Output:
    data/processed/rosters_clean.csv
"""

from __future__ import annotations

import re

import pandas as pd

from src.config import PROCESSED_DATA_DIR


############################
# File paths
############################

INPUT_FILE = (
    PROCESSED_DATA_DIR
    / "rosters_geographic.csv"
)

OUTPUT_FILE = (
    PROCESSED_DATA_DIR
    / "rosters_clean.csv"
)

SEASON = 2025


############################
# Position cleaning
############################

POSITION_MAP = {
    # Outside hitter
    "OH": "OH",
    "OUTSIDE": "OH",
    "OUTSIDE HITTER": "OH",

    # Opposite / right side
    "OPP": "OPP",
    "OPPOSITE": "OPP",
    "OPPOSITE HITTER": "OPP",
    "RS": "OPP",
    "RIGHT SIDE": "OPP",
    "RIGHT SIDE HITTER": "OPP",

    # Middle
    "MB": "MB",
    "MH": "MB",
    "M": "MB",
    "MIDDLE": "MB",
    "MIDDLE BLOCKER": "MB",
    "MIDDLE HITTER": "MB",

    # Libero / defensive specialist
    "L": "L/DS",
    "LIB": "L/DS",
    "LIBERO": "L/DS",
    "DS": "L/DS",
    "DEFENSIVE SPECIALIST": "L/DS",
    "L/DS": "L/DS",
    "DS/L": "L/DS",

    # Setter
    "S": "S",
    "SETTER": "S",
}


def standardize_position(
    value: object,
) -> str:
    """
    Standardize positions into one of:

        OH
        OPP
        MB
        L/DS
        S

    For hybrid positions, the first recognized
    position listed is used.

    Examples:
        OH/DS -> OH
        OH/RS -> OH
        OPP/OH -> OPP
        S/RS -> S
        DS/L -> L/DS
    """

    if pd.isna(value):
        return ""

    text = (
        str(value)
        .strip()
        .upper()
    )

    if not text:
        return ""

    # Direct match.
    if text in POSITION_MAP:
        return POSITION_MAP[
            text
        ]

    # Split hybrid positions.
    parts = re.split(
        r"\s*(?:/|\||,)\s*",
        text,
    )

    for part in parts:
        part = part.strip()

        if part in POSITION_MAP:
            return POSITION_MAP[
                part
            ]

    return ""


############################
# Jersey number cleaning
############################


def clean_jersey_numbers(
    series: pd.Series,
) -> pd.Series:
    """
    Convert jersey numbers to nullable integers.

    Examples:
        1.0 -> 1
        22.0 -> 22
        blank -> missing
    """

    return (
        pd.to_numeric(
            series,
            errors="coerce",
        )
        .astype("Int64")
    )


############################
# Height cleaning
############################


def height_to_inches(
    value: object,
) -> int | pd.NA:
    """
    Convert common volleyball height formats
    into total inches.

    Examples:
        5' 8'' -> 68
        5'9"   -> 69
        6' 2"  -> 74
        6-2    -> 74
    """

    if pd.isna(value):
        return pd.NA

    text = (
        str(value)
        .strip()
    )

    if not text:
        return pd.NA

    # Normalize quote characters.
    text = (
        text
        .replace("’", "'")
        .replace("′", "'")
        .replace("”", '"')
        .replace("″", '"')
    )

    ########################
    # Feet/inches format
    ########################

    match = re.search(
        r"(\d)\s*'\s*(\d{1,2})",
        text,
    )

    if match:
        feet = int(
            match.group(1)
        )

        inches = int(
            match.group(2)
        )

        if (
            4 <= feet <= 7
            and 0 <= inches <= 11
        ):
            return (
                feet * 12
                + inches
            )

    ########################
    # Hyphen format
    ########################

    match = re.fullmatch(
        r"\s*(\d)\s*-\s*(\d{1,2})\s*",
        text,
    )

    if match:
        feet = int(
            match.group(1)
        )

        inches = int(
            match.group(2)
        )

        if (
            4 <= feet <= 7
            and 0 <= inches <= 11
        ):
            return (
                feet * 12
                + inches
            )

    return pd.NA


############################
# Class year cleaning
############################

CLASS_YEAR_MAP = {
    # Freshman
    "FR": "FR",
    "FR.": "FR",
    "FRESHMAN": "FR",

    # Sophomore
    "SO": "SO",
    "SO.": "SO",
    "SOPHOMORE": "SO",

    # Junior
    "JR": "JR",
    "JR.": "JR",
    "JUNIOR": "JR",

    # Senior
    "SR": "SR",
    "SR.": "SR",
    "SENIOR": "SR",

    # Graduate
    "GR": "GR",
    "GR.": "GR",
    "GRAD": "GR",
    "GRAD.": "GR",
    "GRADUATE": "GR",

    # Redshirt freshman
    "R-FR": "R-FR",
    "R-FR.": "R-FR",
    "RS-FR": "R-FR",
    "REDSHIRT FRESHMAN": "R-FR",

    # Redshirt sophomore
    "R-SO": "R-SO",
    "R-SO.": "R-SO",
    "RS-SO": "R-SO",
    "REDSHIRT SOPHOMORE": "R-SO",

    # Redshirt junior
    "R-JR": "R-JR",
    "R-JR.": "R-JR",
    "RS-JR": "R-JR",
    "REDSHIRT JUNIOR": "R-JR",

    # Redshirt senior
    "R-SR": "R-SR",
    "R-SR.": "R-SR",
    "RS-SR": "R-SR",
    "REDSHIRT SENIOR": "R-SR",
}


def standardize_class_year(
    value: object,
) -> str:
    """Standardize class-year labels."""

    if pd.isna(value):
        return ""

    text = (
        str(value)
        .strip()
        .upper()
    )

    if not text:
        return ""

    return CLASS_YEAR_MAP.get(
        text,
        text,
    )


############################
# U.S. state cleaning
############################

US_STATE_MAP = {
    "AL": "AL",
    "ALA": "AL",
    "ALABAMA": "AL",

    "AK": "AK",
    "ALASKA": "AK",

    "AZ": "AZ",
    "ARIZ": "AZ",
    "ARIZONA": "AZ",

    "AR": "AR",
    "ARK": "AR",
    "ARKANSAS": "AR",

    "CA": "CA",
    "CALIF": "CA",
    "CALIFORNIA": "CA",

    "CO": "CO",
    "COLO": "CO",
    "COLORADO": "CO",

    "CT": "CT",
    "CONN": "CT",
    "CONNECTICUT": "CT",

    "DE": "DE",
    "DEL": "DE",
    "DELAWARE": "DE",

    "FL": "FL",
    "FLA": "FL",
    "FLORIDA": "FL",

    "GA": "GA",
    "GEORGIA": "GA",

    "HI": "HI",
    "HAWAII": "HI",

    "ID": "ID",
    "IDAHO": "ID",

    "IL": "IL",
    "ILL": "IL",
    "ILLINOIS": "IL",

    "IN": "IN",
    "IND": "IN",
    "INDIANA": "IN",

    "IA": "IA",
    "IOWA": "IA",

    "KS": "KS",
    "KAN": "KS",
    "KANSAS": "KS",

    "KY": "KY",
    "KENTUCKY": "KY",

    "LA": "LA",
    "LOUISIANA": "LA",

    "ME": "ME",
    "MAINE": "ME",

    "MD": "MD",
    "MARYLAND": "MD",

    "MA": "MA",
    "MASS": "MA",
    "MASSACHUSETTS": "MA",

    "MI": "MI",
    "MICH": "MI",
    "MICHIGAN": "MI",

    "MN": "MN",
    "MINN": "MN",
    "MINNESOTA": "MN",

    "MS": "MS",
    "MISS": "MS",
    "MISSISSIPPI": "MS",

    "MO": "MO",
    "MISSOURI": "MO",

    "MT": "MT",
    "MONT": "MT",
    "MONTANA": "MT",

    "NE": "NE",
    "NEB": "NE",
    "NEBRASKA": "NE",

    "NV": "NV",
    "NEV": "NV",
    "NEVADA": "NV",

    "NH": "NH",
    "NEW HAMPSHIRE": "NH",

    "NJ": "NJ",
    "NEW JERSEY": "NJ",

    "NM": "NM",
    "NEW MEXICO": "NM",

    "NY": "NY",
    "NEW YORK": "NY",

    "NC": "NC",
    "NORTH CAROLINA": "NC",

    "ND": "ND",
    "NORTH DAKOTA": "ND",

    "OH": "OH",
    "OHIO": "OH",

    "OK": "OK",
    "OKLA": "OK",
    "OKLAHOMA": "OK",

    "OR": "OR",
    "ORE": "OR",
    "OREGON": "OR",

    "PA": "PA",
    "PENNSYLVANIA": "PA",

    "RI": "RI",
    "RHODE ISLAND": "RI",

    "SC": "SC",
    "SOUTH CAROLINA": "SC",

    "SD": "SD",
    "SOUTH DAKOTA": "SD",

    "TN": "TN",
    "TENN": "TN",
    "TENNESSEE": "TN",

    "TX": "TX",
    "TEX": "TX",
    "TEXAS": "TX",

    "UT": "UT",
    "UTAH": "UT",

    "VT": "VT",
    "VERMONT": "VT",

    "VA": "VA",
    "VIRGINIA": "VA",

    "WA": "WA",
    "WASH": "WA",
    "WASHINGTON": "WA",

    "WV": "WV",
    "WEST VIRGINIA": "WV",

    "WI": "WI",
    "WIS": "WI",
    "WISC": "WI",
    "WISCONSIN": "WI",

    "WY": "WY",
    "WYO": "WY",
    "WYOMING": "WY",

    "DC": "DC",
    "DISTRICT OF COLUMBIA": "DC",
}


def normalize_state(
    value: str,
) -> str:
    """Convert U.S. state names/abbreviations to two-letter codes."""

    cleaned = (
        value
        .strip()
        .upper()
        .replace(".", "")
    )

    return US_STATE_MAP.get(
        cleaned,
        "",
    )


############################
# Hometown cleaning
############################


def split_hometown(
    value: object,
) -> tuple[
    str,
    str,
    str,
]:
    """
    Split hometown into:

        hometown_city
        hometown_state
        hometown_country

    Examples:

        Wales, Wis.
            -> Wales | WI | USA

        Fairfield, Texas
            -> Fairfield | TX | USA

        Taipei, Taiwan
            -> Taipei | "" | Taiwan

        Karisyaka, Izmir, Turkey
            -> Karisyaka | Izmir | Turkey
    """

    if pd.isna(value):
        return (
            "",
            "",
            "",
        )

    text = (
        str(value)
        .strip()
    )

    if not text:
        return (
            "",
            "",
            "",
        )

    parts = [
        part.strip()
        for part
        in text.split(",")
        if part.strip()
    ]

    ########################
    # Only city available
    ########################

    if len(parts) == 1:
        return (
            parts[0],
            "",
            "",
        )

    ########################
    # City + state/country
    ########################

    if len(parts) == 2:
        city = parts[0]

        second = parts[1]

        state = normalize_state(
            second
        )

        if state:
            return (
                city,
                state,
                "USA",
            )

        return (
            city,
            "",
            second,
        )

    ########################
    # City + region + country
    ########################

    city = parts[0]

    country = parts[-1]

    region = ", ".join(
        parts[1:-1]
    )

    # Check whether the middle value
    # is actually a U.S. state.
    state = normalize_state(
        region
    )

    if state:
        return (
            city,
            state,
            "USA",
        )

    return (
        city,
        region,
        country,
    )


############################
# Main cleaning pipeline
############################


def main() -> None:
    """Create the final analysis-ready roster dataset."""

    df = pd.read_csv(
        INPUT_FILE,
        encoding="utf-8-sig",
    )

    print(
        "\nStarting roster cleaning..."
    )

    print(
        f"Starting rows: {len(df)}"
    )

    ############################
    # Remove exact duplicates
    ############################

    starting_rows = len(
        df
    )

    df = (
        df
        .drop_duplicates()
        .copy()
    )

    duplicates_removed = (
        starting_rows
        - len(df)
    )

    ############################
    # Jersey numbers
    ############################

    df[
        "jersey_number"
    ] = clean_jersey_numbers(
        df[
            "jersey_number"
        ]
    )

    ############################
    # Positions
    ############################

    df[
        "position"
    ] = df[
        "position"
    ].apply(
        standardize_position
    )

    ############################
    # Heights
    ############################

    df[
        "height_inches"
    ] = df[
        "height"
    ].apply(
        height_to_inches
    )

    # Use nullable integer type.
    df[
        "height_inches"
    ] = df[
        "height_inches"
    ].astype(
        "Int64"
    )

    # Remove original height string.
    df = df.drop(
        columns=[
            "height",
        ]
    )

    ############################
    # Class years
    ############################

    df[
        "class_year"
    ] = df[
        "class_year"
    ].apply(
        standardize_class_year
    )

    ############################
    # Hometown geography
    ############################

    geography = df[
        "hometown"
    ].apply(
        split_hometown
    )

    df[
        "hometown_city"
    ] = geography.apply(
        lambda item:
        item[0]
    )

    df[
        "hometown_state"
    ] = geography.apply(
        lambda item:
        item[1]
    )

    df[
        "hometown_country"
    ] = geography.apply(
        lambda item:
        item[2]
    )

    # Remove original combined hometown.
    df = df.drop(
        columns=[
            "hometown",
        ]
    )

    ############################
    # Add season
    ############################

    df[
        "season"
    ] = SEASON

    ############################
    # Remove temporary columns
    ############################

    temporary_columns = [
        "valid_player",
        "valid_hometown",
    ]

    df = df.drop(
        columns=[
            column
            for column
            in temporary_columns
            if column in df.columns
        ]
    )

    ############################
    # Remove duplicates again
    # after standardization
    ############################

    before_final_duplicates = len(
        df
    )

    df = (
        df
        .drop_duplicates()
        .reset_index(
            drop=True
        )
    )

    standardized_duplicates_removed = (
        before_final_duplicates
        - len(df)
    )

    ############################
    # Save
    ############################

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    ############################
    # Cleaning summary
    ############################

    print(
        "\nCleaning complete!"
    )

    print(
        f"Exact duplicates removed "
        f"before cleaning: "
        f"{duplicates_removed}"
    )

    print(
        f"Duplicates removed after "
        f"standardization: "
        f"{standardized_duplicates_removed}"
    )

    print(
        f"Final player rows: "
        f"{len(df)}"
    )

    print(
        "\nPosition counts:"
    )

    print(
        df[
            "position"
        ]
        .value_counts(
            dropna=False
        )
    )

    print(
        "\nClass-year counts:"
    )

    print(
        df[
            "class_year"
        ]
        .value_counts(
            dropna=False
        )
    )

    print(
        "\nPlayers with height data:"
    )

    print(
        df[
            "height_inches"
        ]
        .notna()
        .sum()
    )

    print(
        "\nPlayers with U.S. state data:"
    )

    print(
        df[
            "hometown_state"
        ]
        .ne("")
        .sum()
    )

    print(
        "\nSaved cleaned dataset to:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()