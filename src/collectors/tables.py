"""Parser for roster pages containing standard HTML tables."""

from io import StringIO

import pandas as pd

from src.collectors.common import standardize_roster


IDENTIFYING_COLUMNS = {
    "name",
    "pos.",
    "ht.",
    "yr.",
    "hometown",
}


def extract_table_roster(html: str) -> pd.DataFrame:
    """Extract a roster from a standard HTML table."""

    tables = pd.read_html(StringIO(html))

    for table in tables:
        candidate_df = table.copy()

        if isinstance(candidate_df.columns, pd.MultiIndex):
            candidate_df.columns = [
                " ".join(
                    str(part).strip()
                    for part in column
                    if str(part).strip().lower() != "nan"
                )
                for column in candidate_df.columns
            ]

        normalized_columns = {
            str(column).strip().lower()
            for column in candidate_df.columns
        }

        has_name = bool(
            {"name", "player", "student-athlete"}
            & normalized_columns
        )

        has_roster_details = len(
            {
                "pos.",
                "pos",
                "position",
                "ht.",
                "height",
                "yr.",
                "year",
                "hometown",
            }
            & normalized_columns
        ) >= 2

        if has_name and has_roster_details:
            return standardize_roster(candidate_df)

    raise ValueError("No recognizable roster table was found.")