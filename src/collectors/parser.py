"""Universal roster parser supporting multiple athletics-site layouts."""

from collections.abc import Callable

import pandas as pd

from src.collectors.common import validate_roster
from src.collectors.sidearm import extract_sidearm_roster
from src.collectors.tables import extract_table_roster
from src.collectors.labeled_cards import (
    extract_labeled_card_roster,
)
from src.collectors.visible_text import (
    extract_compact_text_roster,
)


RosterParser = Callable[[str], pd.DataFrame]


PARSERS: dict[str, RosterParser] = {
    "table": extract_table_roster,
    "labeled_cards": extract_labeled_card_roster,
    "sidearm": extract_sidearm_roster,
}


PLATFORM_PRIORITY: dict[str, list[str]] = {
    "sidearm": [
        "table",
        "labeled_cards",
        "sidearm",
    ],
    "table": [
        "table",
        "labeled_cards",
    ],
    "unknown": [
        "table",
        "labeled_cards",
        "sidearm",
    ],
}


def extract_roster(
    html: str,
    *,
    platform: str = "unknown",
) -> tuple[pd.DataFrame, str]:
    """
    Extract roster data using the best available parser.

    Returns:
        A tuple containing the standardized roster DataFrame and the
        name of the parser that succeeded.
    """

    normalized_platform = str(platform).strip().lower()

    parser_order = PLATFORM_PRIORITY.get(
        normalized_platform,
        PLATFORM_PRIORITY["unknown"],
    )

    parser_errors: list[str] = []

    for parser_name in parser_order:
        parser = PARSERS[parser_name]

        try:
            roster_df = parser(html)
            validate_roster(roster_df)

            return roster_df, parser_name

        except (ValueError, ImportError) as error:
            parser_errors.append(
                f"{parser_name}: {error}"
            )

    error_summary = " | ".join(parser_errors)

    raise ValueError(
        "Every available roster parser failed. "
        f"{error_summary}"
    )