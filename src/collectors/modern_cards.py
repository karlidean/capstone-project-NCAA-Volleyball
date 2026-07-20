"""Parser for modern compact roster-card layouts."""

from __future__ import annotations

import re

import pandas as pd
from bs4 import BeautifulSoup, Tag

from src.collectors.common import standardize_roster


NAME_PATTERN = re.compile(
    r"^[A-Za-zÀ-ÖØ-öø-ÿ'’.\-]+"
    r"(?:\s+[A-Za-zÀ-ÖØ-öø-ÿ'’.\-]+)+$"
)

HEIGHT_PATTERN = re.compile(
    r"^\d['’]\s*\d{1,2}[\"”]?$"
)

JERSEY_PATTERN = re.compile(
    r"^#?\d{1,2}$"
)

CLASS_PATTERN = re.compile(
    r"^(?:Fr\.?|So\.?|Jr\.?|Sr\.?|Gr\.?|"
    r"Freshman|Sophomore|Junior|Senior|Graduate|"
    r"R-Fr\.?|R-So\.?|R-Jr\.?|R-Sr\.?|"
    r"Fr-1|Fr-2|So-1|So-2|Jr-1|Jr-2|Sr-1|Sr-2)$",
    re.IGNORECASE,
)

POSITION_PATTERN = re.compile(
    r"^(?:"
    r"OH|MB|MH|S|DS|L|LIB|OPP|RS|"
    r"OH/L|OH/OPP|S/RS|DS/L|L/DS|"
    r"Outside Hitter|Middle Blocker|Middle Hitter|"
    r"Setter|Libero|Defensive Specialist|"
    r"Opposite|Right Side"
    r")$",
    re.IGNORECASE,
)


def clean_text(value: str) -> str:
    """Normalize whitespace in one text value."""

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def get_clean_lines(element: Tag) -> list[str]:
    """Return clean nonempty text lines from one card."""

    lines = [
        clean_text(line)
        for line in element.get_text(
            "\n",
            strip=True,
        ).splitlines()
    ]

    return [
        line
        for line in lines
        if line
    ]


def looks_like_player_card(
    element: Tag,
) -> bool:
    """Return True when an element resembles one player card."""

    lines = get_clean_lines(
        element
    )

    if len(lines) < 3:
        return False

    expanded_lines = expand_lines(
        lines
    )

    has_name = any(
        NAME_PATTERN.fullmatch(line)
        for line in expanded_lines
    )

    has_height = any(
        HEIGHT_PATTERN.fullmatch(line)
        for line in expanded_lines
    )

    has_position = any(
        POSITION_PATTERN.fullmatch(line)
        for line in expanded_lines
    )

    return (
        has_name
        and (
            has_height
            or has_position
        )
    )


def find_candidate_cards(
    soup: BeautifulSoup,
) -> list[Tag]:
    """Locate likely modern roster-card containers."""

    selectors = [
        "[class*='roster-player']",
        "[class*='roster_player']",
        "[class*='roster-item']",
        "[class*='roster_item']",
        "[class*='player-card']",
        "[class*='player_card']",
        "[class*='person-card']",
        "[class*='person_card']",
        "[class*='s-person-card']",
        "[class*='sidearm-roster-player']",
        "li[class*='roster']",
        "article[class*='roster']",
    ]

    candidates: list[Tag] = []
    seen_ids: set[int] = set()

    for selector in selectors:
        for element in soup.select(
            selector
        ):
            if not isinstance(
                element,
                Tag,
            ):
                continue

            element_id = id(
                element
            )

            if element_id in seen_ids:
                continue

            seen_ids.add(
                element_id
            )

            if looks_like_player_card(
                element
            ):
                candidates.append(
                    element
                )

    return candidates


def split_metadata_line(
    line: str,
) -> list[str]:
    """
    Split compact metadata such as:

    OH / So. / 5'9"
    MB | R-Jr. | 6'2"
    """

    parts = re.split(
        r"\s*(?:/|\||·|•)\s*",
        line,
    )

    return [
        clean_text(part)
        for part in parts
        if clean_text(part)
    ]


def expand_lines(
    lines: list[str],
) -> list[str]:
    """Expand slash-, pipe-, or bullet-separated metadata."""

    expanded: list[str] = []

    for line in lines:
        expanded.append(
            line
        )

        parts = split_metadata_line(
            line
        )

        if len(parts) > 1:
            expanded.extend(
                parts
            )

    return expanded


def extract_name(
    lines: list[str],
) -> str:
    """Find the most likely player name."""

    ignored_terms = {
        "full bio",
        "bio",
        "roster",
        "volleyball",
    }

    for line in lines:
        normalized = (
            line.lower()
        )

        if normalized in ignored_terms:
            continue

        if POSITION_PATTERN.fullmatch(
            line
        ):
            continue

        if CLASS_PATTERN.fullmatch(
            line
        ):
            continue

        if (
            NAME_PATTERN.fullmatch(
                line
            )
        ):
            return line

    return ""


def extract_jersey(
    lines: list[str],
) -> str:
    """Find a jersey number."""

    for line in lines:
        if JERSEY_PATTERN.fullmatch(
            line
        ):
            return line.lstrip(
                "#"
            )

    return ""


def extract_height(
    lines: list[str],
) -> str:
    """Find player height."""

    for line in lines:
        if HEIGHT_PATTERN.fullmatch(
            line
        ):
            return line

    return ""


def extract_position(
    lines: list[str],
) -> str:
    """Find player position."""

    for line in lines:
        if POSITION_PATTERN.fullmatch(
            line
        ):
            return line

    return ""


def extract_class_year(
    lines: list[str],
) -> str:
    """Find player academic class."""

    for line in lines:
        if CLASS_PATTERN.fullmatch(
            line
        ):
            return line

    return ""


def extract_location_fields(
    lines: list[str],
    *,
    player_name: str,
    jersey_number: str,
    position: str,
    height: str,
    class_year: str,
) -> tuple[str, str]:
    """
    Infer hometown and high school from remaining card text.

    The first plausible leftover line becomes hometown.
    The second becomes high school.
    """

    skip_values = {
        player_name,
        jersey_number,
        f"#{jersey_number}"
        if jersey_number
        else "",
        position,
        height,
        class_year,
        "Full Bio",
    }

    leftovers: list[str] = []

    for line in lines:
        if not line:
            continue

        if line in skip_values:
            continue

        if JERSEY_PATTERN.fullmatch(
            line
        ):
            continue

        if HEIGHT_PATTERN.fullmatch(
            line
        ):
            continue

        if POSITION_PATTERN.fullmatch(
            line
        ):
            continue

        if CLASS_PATTERN.fullmatch(
            line
        ):
            continue

        lowered = (
            line.lower()
        )

        if any(
            phrase in lowered
            for phrase in (
                "full bio",
                "instagram",
                "twitter",
                "roster",
                "jump to",
                "coaching staff",
            )
        ):
            continue

        leftovers.append(
            line
        )

    hometown = (
        leftovers[0]
        if leftovers
        else ""
    )

    high_school = (
        leftovers[1]
        if len(leftovers) > 1
        else ""
    )

    return (
        hometown,
        high_school,
    )


def parse_card(
    card: Tag,
) -> dict[str, str]:
    """Parse one modern roster card."""

    raw_lines = get_clean_lines(
        card
    )

    lines = expand_lines(
        raw_lines
    )

    player_name = extract_name(
        lines
    )

    jersey_number = extract_jersey(
        lines
    )

    position = extract_position(
        lines
    )

    height = extract_height(
        lines
    )

    class_year = extract_class_year(
        lines
    )

    (
        hometown,
        high_school,
    ) = extract_location_fields(
        raw_lines,
        player_name=player_name,
        jersey_number=jersey_number,
        position=position,
        height=height,
        class_year=class_year,
    )

    return {
        "jersey_number":
            jersey_number,
        "player_name":
            player_name,
        "position":
            position,
        "height":
            height,
        "class_year":
            class_year,
        "hometown":
            hometown,
        "high_school":
            high_school,
        "previous_school":
            "",
    }


def extract_modern_card_roster(
    html: str,
) -> pd.DataFrame:
    """Extract roster data from modern card/list layouts."""

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    cards = find_candidate_cards(
        soup
    )

    if not cards:
        raise ValueError(
            "No modern roster-card containers were found."
        )

    records: list[
        dict[str, str]
    ] = []

    for card in cards:
        record = parse_card(
            card
        )

        if not record[
            "player_name"
        ]:
            continue

        records.append(
            record
        )

    if not records:
        raise ValueError(
            "Modern roster cards were found, "
            "but no player records were extracted."
        )

    roster_df = standardize_roster(
        pd.DataFrame(
            records
        )
    )

    if len(roster_df) < 5:
        raise ValueError(
            "Modern-card parser extracted "
            f"only {len(roster_df)} players."
        )

    return roster_df