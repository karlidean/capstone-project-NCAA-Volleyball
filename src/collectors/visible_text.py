"""Parsers for roster data extracted from rendered visible text."""

import re

import pandas as pd

from src.collectors.common import standardize_roster


HEIGHT_PATTERN = re.compile(
    r"^\d+'\s*\d+(?:''|\")$"
)

CLASS_PATTERN = re.compile(
    r"^(?:Fr\.?|So\.?|Jr\.?|Sr\.?|Gr\.?|"
    r"R-Fr\.?|R-So\.?|R-Jr\.?|R-Sr\.?)$",
    re.IGNORECASE,
)


def split_hometown_school(value: str) -> tuple[str, str]:
    """Split a combined hometown and high-school value."""

    if " / " not in value:
        return value.strip(), ""

    hometown, high_school = value.split(
        " / ",
        maxsplit=1,
    )

    return hometown.strip(), high_school.strip()


def extract_compact_text_roster(
    visible_text: str,
) -> pd.DataFrame:
    """
    Extract roster rows from tab-separated rendered page text.

    Expected example:
        1    Madi Sell    6' 3''    MB    Jr.
        Ballwin, Mo. / Marquette    Missouri    madilynsell
    """

    records: list[dict] = []

    for raw_line in visible_text.splitlines():
        if "\t" not in raw_line:
            continue

        fields = [
            field.strip()
            for field in raw_line.split("\t")
        ]

        # Keep meaningful values but preserve ordering.
        nonempty_fields = [
            field
            for field in fields
            if field
        ]

        if len(nonempty_fields) < 6:
            continue

        jersey_number = nonempty_fields[0]
        player_name = nonempty_fields[1]
        height = nonempty_fields[2]
        position = nonempty_fields[3]
        class_year = nonempty_fields[4]
        location_school = nonempty_fields[5]

        if not jersey_number.isdigit():
            continue

        if not HEIGHT_PATTERN.match(height):
            continue

        if not CLASS_PATTERN.match(class_year):
            continue

        hometown, high_school = split_hometown_school(
            location_school
        )

        previous_school = ""

        if len(nonempty_fields) >= 7:
            possible_previous_school = nonempty_fields[6]

            # Ignore profile slugs such as "madilynsell".
            looks_like_slug = (
                " " not in possible_previous_school
                and possible_previous_school.islower()
                and possible_previous_school.isalpha()
            )

            if not looks_like_slug:
                previous_school = possible_previous_school

        records.append(
            {
                "jersey_number": jersey_number,
                "player_name": player_name,
                "height": height,
                "position": position,
                "class_year": class_year,
                "hometown": hometown,
                "high_school": high_school,
                "previous_school": previous_school,
            }
        )

    if not records:
        raise ValueError(
            "No tab-separated visible-text roster rows were found."
        )

    return standardize_roster(
        pd.DataFrame(records)
    )