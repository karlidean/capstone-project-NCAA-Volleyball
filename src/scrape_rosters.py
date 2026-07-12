"""
src.scrape_rosters.py

This is the script for scraping NCAA volleyball roster data and
saving it as a CSV in the data/raw directory.
"""

#######################
# Imports
#######################

import pandas as pd
from src.config import RAW_DATA_DIR, HEADERS, REQUEST_DELAY

def save_roster_csv(roster_data: list[dict], filename: str) -> None:
    """
    Save the roster data as a CSV file in the raw data directory.

    Args:
        roster_data (list[dict]): List of dictionaries containing roster data and player records.
        filename (str): Name of the CSV file to save.
    """
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists

    roster_df = pd.DataFrame(roster_data)

    output_path = RAW_DATA_DIR / filename

    roster_df.to_csv(output_path, index=False)

    print(f"Saved {len(roster_df)} roster records to {output_path}")

    print(output_path)

def main() -> None:
    """
    Main function to scrape NCAA volleyball roster data and save it as a CSV.
    """
    # Placeholder for the actual scraping logic
    # This is where you would implement the scraping of roster data
    # For demonstration purposes, we'll use a sample list of dictionaries

    sample_roster_data = [
        {
            "player_name": "Jane Smith",
            "position": "Outside Hitter",
            "height": "6-1",
            "class_year": "Senior",
            "hometown": "St. Louis, Missouri",
            "previous_school": "",
            "team": "Example University",
            "season": 2025,
        },
        {
            "player_name": "Taylor Jones",
            "position": "Setter",
            "height": "5-10",
            "class_year": "Junior",
            "hometown": "Kansas City, Missouri",
            "previous_school": "Example State",
            "team": "Example University",
            "season": 2025,
        },
    ]

    save_roster_csv(sample_roster_data, "sample_roster.csv")

if __name__ == "__main__":
    main()