"""
enrich_schools.py

This script will enrich the school catalog with athletics site source info.
"""

import pandas as pd

from src.config import SCHOOL_SOURCES_FILE, SCHOOLS_FILE


SOURCE_COLUMNS = [
    "school_code",
    "athletics_domain",
    "roster_url_template",
    "platform",
]


def load_school_catalog() -> pd.DataFrame:
    """Load the base school catalog."""

    schools_df = pd.read_csv(SCHOOLS_FILE)

    if schools_df.empty:
        raise ValueError("The school catalog is empty.")

    return schools_df


def load_school_sources() -> pd.DataFrame:
    """Load manually verified athletics-site source information."""

    sources_df = pd.read_csv(SCHOOL_SOURCES_FILE)

    missing_columns = set(SOURCE_COLUMNS).difference(sources_df.columns)

    if missing_columns:
        raise ValueError(
            "The source catalog is missing columns: "
            f"{sorted(missing_columns)}"
        )

    duplicated_codes = sources_df[
        sources_df["school_code"].duplicated(keep=False)
    ]

    if not duplicated_codes.empty:
        duplicates = sorted(
            duplicated_codes["school_code"].unique()
        )

        raise ValueError(
            f"Duplicate school codes in source catalog: {duplicates}"
        )

    return sources_df[SOURCE_COLUMNS].copy()


def enrich_school_catalog(
    schools_df: pd.DataFrame,
    sources_df: pd.DataFrame,
) -> pd.DataFrame:
    """Merge source information into the base school catalog."""

    # Remove placeholder source fields before merging replacements.
    fields_to_replace = [
        "athletics_domain",
        "roster_url_template",
        "platform",
    ]

    schools_df = schools_df.drop(
        columns=[
            column
            for column in fields_to_replace
            if column in schools_df.columns
        ]
    )

    enriched_df = schools_df.merge(
        sources_df,
        on="school_code",
        how="left",
        validate="one_to_one",
    )

    enriched_df["platform"] = enriched_df["platform"].fillna(
        "unknown"
    )

    return enriched_df


def validate_matches(
    schools_df: pd.DataFrame,
    sources_df: pd.DataFrame,
) -> None:
    """Confirm every source record matches a school catalog record."""

    unmatched_codes = sorted(
        set(sources_df["school_code"])
        - set(schools_df["school_code"])
    )

    if unmatched_codes:
        raise ValueError(
            "These source school codes do not match schools.csv: "
            f"{unmatched_codes}"
        )


def print_summary(schools_df: pd.DataFrame) -> None:
    """Display enrichment coverage by conference."""

    summary_df = (
        schools_df.assign(
            source_configured=schools_df[
                "roster_url_template"
            ].notna()
        )
        .groupby("current_conference_code")[
            "source_configured"
        ]
        .agg(["sum", "count"])
        .rename(
            columns={
                "sum": "configured",
                "count": "total",
            }
        )
    )

    summary_df["remaining"] = (
        summary_df["total"] - summary_df["configured"]
    )

    print("\nSource coverage by conference:")
    print(summary_df)


def save_school_catalog(schools_df: pd.DataFrame) -> None:
    """Overwrite schools.csv with its enriched version."""

    schools_df.to_csv(
        SCHOOLS_FILE,
        index=False,
    )

    print(f"\nUpdated {len(schools_df)} schools in:")
    print(SCHOOLS_FILE)


def main() -> None:
    """Run the school-catalog enrichment process."""

    schools_df = load_school_catalog()
    sources_df = load_school_sources()

    validate_matches(
        schools_df,
        sources_df,
    )

    enriched_df = enrich_school_catalog(
        schools_df,
        sources_df,
    )

    print_summary(enriched_df)
    save_school_catalog(enriched_df)


if __name__ == "__main__":
    main()