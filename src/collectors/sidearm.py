"""Parser for Sidearm roster pages using player cards."""

import pandas as pd
from bs4 import BeautifulSoup

from src.collectors.common import standardize_roster


FIELD_SELECTORS = {
    "jersey_number": [
        ".sidearm-roster-player-jersey-number",
        ".sidearm-roster-player-number",
    ],
    "player_name": [
        ".sidearm-roster-player-name",
        ".sidearm-roster-player-name a",
    ],
    "position": [
        ".sidearm-roster-player-position",
    ],
    "height": [
        ".sidearm-roster-player-height",
    ],
    "class_year": [
        ".sidearm-roster-player-academic-year",
        ".sidearm-roster-player-year",
    ],
    "hometown": [
        ".sidearm-roster-player-hometown",
    ],
    "high_school": [
        ".sidearm-roster-player-highschool",
        ".sidearm-roster-player-high-school",
    ],
    "previous_school": [
        ".sidearm-roster-player-previous-school",
    ],
}


def get_first_text(card, selectors: list[str]) -> str:
    """Return text from the first selector found inside a player card."""

    for selector in selectors:
        element = card.select_one(selector)

        if element is not None:
            text = element.get_text(" ", strip=True)

            if text:
                return text

    return ""


def extract_sidearm_roster(html: str) -> pd.DataFrame:
    """Extract roster records from Sidearm player cards."""

    soup = BeautifulSoup(html, "html.parser")

    player_cards = soup.select(
        "li.sidearm-roster-player, "
        "div.sidearm-roster-player"
    )

    if not player_cards:
        raise ValueError("No Sidearm player cards were found.")

    records: list[dict] = []

    for card in player_cards:
        record = {
            field: get_first_text(card, selectors)
            for field, selectors in FIELD_SELECTORS.items()
        }

        if record["player_name"]:
            records.append(record)

    if not records:
        raise ValueError(
            "Sidearm cards were found, but player names were not extracted."
        )

    return standardize_roster(pd.DataFrame(records))