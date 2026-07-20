from __future__ import annotations

import re

import pandas as pd

from src.config import (
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
)


INPUT_FILE = RAW_DATA_DIR / "rosters.csv"

OUTPUT_FILE = (
    PROCESSED_DATA_DIR
    / "rosters_geographic.csv"
)


INVALID_PLAYER_NAMES = {
    "jersey number",
    "academic year",
    "go to coaching staff",
    "players",
    "position",
    "height",
    "print",
    "download",
    "full bio",
    "outside hitter",
    "middle blocker",
    "middle hitter",
    "right side hitter",
    "setter",
    "libero",
    "defensive specialist",
}


INVALID_GEOGRAPHY_VALUES = {
    "players",
    "position",
    "height",
    "jersey number",
    "academic year",
    "print",
    "download",
    "go",
    "full bio",
    "middle blocker",
    "right side hitter",
    "outside hitter",
    "defensive specialist",
    "setter",
    "libero",
    "mb",
    "oh",
    "rs",
    "ds",
    "l",
    "s",
    "mb/rs",
    "oh/rs",
    "oh/ds",
    "ds/l",
}


def clean_value(
    value: object,
) -> str:
    """Convert a value into normalized text."""

    if pd.isna(value):
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value),
    ).strip()


def valid_player_name(
    value: object,
) -> bool:
    """Reject obvious non-player parser artifacts."""

    text = clean_value(
        value
    )

    if not text:
        return False

    return (
        text.lower()
        not in INVALID_PLAYER_NAMES
    )


def valid_hometown(
    value: object,
) -> bool:
    """
    Keep hometown values that resemble:

        City, State
        City, State Abbreviation
        City, Country
        City, Region, Country
    """

    text = clean_value(
        value
    )

    if not text:
        return False

    if (
        text.lower()
        in INVALID_GEOGRAPHY_VALUES
    ):
        return False

    # Require at least one comma.
    # This catches formats such as:
    #
    # Wales, Wis.
    # Dallas, TX
    # Taipei, Taiwan
    # Toronto, Ontario, Canada
    if "," not in text:
        return False

    parts = [
        part.strip()
        for part
        in text.split(",")
        if part.strip()
    ]

    # Must contain at least:
    # city + state/region/country
    if len(parts) < 2:
        return False

    # Reject obvious shifted volleyball metadata.
    if any(
        part.lower()
        in INVALID_GEOGRAPHY_VALUES
        for part
        in parts
    ):
        return False

    # Require the city portion to contain letters.
    if not re.search(
        r"[A-Za-zÀ-ÖØ-öø-ÿ]",
        parts[0],
    ):
        return False

    return True


def main() -> None:
    """Create a geography-ready player dataset."""

    df = pd.read_csv(
        INPUT_FILE,
        encoding="utf-8-sig",
    )

    required_columns = {
        "player_name",
        "hometown",
        "school_name",
        "division",
        "conference_code",
    }

    missing_columns = (
        required_columns
        - set(df.columns)
    )

    if missing_columns:
        raise ValueError(
            "rosters.csv is missing: "
            + ", ".join(
                sorted(
                    missing_columns
                )
            )
        )

    ############################
    # Validation flags
    ############################

    df[
        "valid_player"
    ] = df[
        "player_name"
    ].apply(
        valid_player_name
    )

    df[
        "valid_hometown"
    ] = df[
        "hometown"
    ].apply(
        valid_hometown
    )

    ############################
    # Filter
    ############################

    filtered_df = df[
        df["valid_player"]
        & df["valid_hometown"]
    ].copy()

    ############################
    # Save
    ############################

    PROCESSED_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    filtered_df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    ############################
    # Summary
    ############################

    print(
        f"Original rows: "
        f"{len(df)}"
    )

    print(
        f"Valid player rows: "
        f"{df['valid_player'].sum()}"
    )

    print(
        f"Rows with usable hometowns: "
        f"{df['valid_hometown'].sum()}"
    )

    print(
        f"Final geography dataset: "
        f"{len(filtered_df)}"
    )

    print(
        f"Rows removed: "
        f"{len(df) - len(filtered_df)}"
    )

    print(
        "\nSaved to:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()