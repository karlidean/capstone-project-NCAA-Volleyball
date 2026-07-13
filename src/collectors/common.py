"""Shared roster parsing and validation utilities."""

import pandas as pd


ROSTER_COLUMNS = [
    "jersey_number",
    "player_name",
    "position",
    "height",
    "class_year",
    "hometown",
    "high_school",
    "previous_school",
]


COLUMN_ALIASES = {
    "#": "jersey_number",
    "no": "jersey_number",
    "no.": "jersey_number",
    "number": "jersey_number",
    "jersey": "jersey_number",
    "jersey number": "jersey_number",
    "name": "player_name",
    "player": "player_name",
    "student-athlete": "player_name",
    "student athlete": "player_name",
    "pos": "position",
    "pos.": "position",
    "position": "position",
    "ht": "height",
    "ht.": "height",
    "height": "height",
    "yr": "class_year",
    "yr.": "class_year",
    "year": "class_year",
    "class": "class_year",
    "academic year": "class_year",
    "hometown": "hometown",
    "home town": "hometown",
    "high school": "high_school",
    "highschool": "high_school",
    "previous school": "previous_school",
    "prior school": "previous_school",
}


def flatten_columns(roster_df: pd.DataFrame) -> pd.DataFrame:
    """Flatten pandas MultiIndex columns when present."""

    roster_df = roster_df.copy()

    if isinstance(roster_df.columns, pd.MultiIndex):
        roster_df.columns = [
            " ".join(
                str(part).strip()
                for part in column
                if str(part).strip().lower() != "nan"
            )
            for column in roster_df.columns
        ]

    return roster_df


def standardize_roster(roster_df: pd.DataFrame) -> pd.DataFrame:
    """Convert a roster DataFrame into the project's standard schema."""

    roster_df = flatten_columns(roster_df)

    roster_df.columns = [
        str(column).strip().lower()
        for column in roster_df.columns
    ]

    roster_df = roster_df.rename(columns=COLUMN_ALIASES)

    for column in ROSTER_COLUMNS:
        if column not in roster_df.columns:
            roster_df[column] = pd.NA

    roster_df = roster_df[ROSTER_COLUMNS].copy()

    for column in ROSTER_COLUMNS:
        roster_df[column] = (
            roster_df[column]
            .astype("string")
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
        )

    roster_df = roster_df[
        roster_df["player_name"].notna()
        & roster_df["player_name"].ne("")
    ].copy()

    roster_df = roster_df.drop_duplicates(
        subset=["player_name", "jersey_number"],
        keep="first",
    )

    return roster_df.reset_index(drop=True)


def validate_roster(roster_df: pd.DataFrame) -> None:
    """Raise an error when extracted roster data is unusable."""

    if roster_df.empty:
        raise ValueError("The parser returned an empty roster.")

    if "player_name" not in roster_df.columns:
        raise ValueError("The roster has no player_name column.")

    named_player_count = roster_df["player_name"].notna().sum()

    if named_player_count == 0:
        raise ValueError("The roster contains no player names.")

    if named_player_count < 5:
        raise ValueError(
            f"Only {named_player_count} players were extracted."
        )