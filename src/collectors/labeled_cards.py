"""Parser for modern roster cards containing labeled player fields."""

import re

import pandas as pd
from bs4 import BeautifulSoup

from src.collectors.common import standardize_roster


FIELD_PATTERNS = {
    "position": re.compile(
        r"^Position\s+(.+)$",
        re.IGNORECASE,
    ),
    "class_year": re.compile(
        r"^(?:Academic Year|Class)\s+(.+)$",
        re.IGNORECASE,
    ),
    "height": re.compile(
        r"^Height\s+(.+)$",
        re.IGNORECASE,
    ),
    "hometown": re.compile(
        r"^Hometown\s+(.+)$",
        re.IGNORECASE,
    ),
    "high_school": re.compile(
        r"^(?:Last School|High School)\s+(.+)$",
        re.IGNORECASE,
    ),
    "previous_school": re.compile(
        r"^Previous School(?::|\s)+(.+)$",
        re.IGNORECASE,
    ),
}


def clean_lines(html: str) -> list[str]:
    """Convert webpage HTML into cleaned, nonempty text lines."""

    soup = BeautifulSoup(html, "html.parser")

    for unwanted in soup(
        ["script", "style", "noscript", "svg"]
    ):
        unwanted.decompose()

    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in soup.get_text("\n").splitlines()
    ]

    return [
        line
        for line in lines
        if line
    ]


def split_player_blocks(lines: list[str]) -> list[list[str]]:
    """Split visible page text into blocks beginning with Jersey Number."""

    blocks: list[list[str]] = []
    current_block: list[str] = []

    for line in lines:
        if re.match(
            r"^Jersey Number\s+\S+",
            line,
            re.IGNORECASE,
        ):
            if current_block:
                blocks.append(current_block)

            current_block = [line]

        elif current_block:
            current_block.append(line)

    if current_block:
        blocks.append(current_block)

    return blocks


def extract_jersey_number(line: str) -> str:
    """Extract the jersey number from a block's first line."""

    match = re.match(
        r"^Jersey Number\s+(.+)$",
        line,
        re.IGNORECASE,
    )

    return match.group(1).strip() if match else ""


def find_player_name(block: list[str]) -> str:
    """Find the player name immediately following the jersey number."""

    ignored_prefixes = (
        "position ",
        "academic year ",
        "class ",
        "height ",
        "hometown ",
        "last school ",
        "high school ",
        "previous school",
        "full bio ",
        "expand for ",
        "skip ad",
    )

    for line in block[1:6]:
        normalized_line = line.lower()

        if normalized_line.startswith(ignored_prefixes):
            continue

        if re.fullmatch(
            r"[A-Za-zÀ-ÖØ-öø-ÿ'’.\- ]{2,}",
            line,
        ):
            return line

    return ""


def extract_field(
    block: list[str],
    field_name: str,
) -> str:
    """Extract one labeled roster field from a player block."""

    pattern = FIELD_PATTERNS[field_name]

    for line in block:
        match = pattern.match(line)

        if match:
            return match.group(1).strip()

    return ""


def extract_labeled_card_roster(html: str) -> pd.DataFrame:
    """Extract roster data from modern labeled player cards."""

    lines = clean_lines(html)
    blocks = split_player_blocks(lines)

    if not blocks:
        raise ValueError(
            "No labeled Jersey Number player blocks were found."
        )

    records: list[dict] = []

    for block in blocks:
        player_name = find_player_name(block)

        if not player_name:
            continue

        records.append(
            {
                "jersey_number": extract_jersey_number(
                    block[0]
                ),
                "player_name": player_name,
                "position": extract_field(
                    block,
                    "position",
                ),
                "height": extract_field(
                    block,
                    "height",
                ),
                "class_year": extract_field(
                    block,
                    "class_year",
                ),
                "hometown": extract_field(
                    block,
                    "hometown",
                ),
                "high_school": extract_field(
                    block,
                    "high_school",
                ),
                "previous_school": extract_field(
                    block,
                    "previous_school",
                ),
            }
        )

    if not records:
        raise ValueError(
            "Labeled player blocks were found, "
            "but no player records were extracted."
        )

    roster_df = standardize_roster(
        pd.DataFrame(records)
    )

    return roster_df