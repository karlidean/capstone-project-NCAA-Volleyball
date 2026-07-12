"""
Project Configuration Settings File

This module centralizes all file paths and constants 
for the recruiting analysis project.
"""

from pathlib import Path

#####################################
# Project Directory Paths
#####################################

# Repository Root
PROJECT_ROOT = Path(__file__).parent.parent

# Data Folders
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Other Project Folders
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
DOCS_DIR = PROJECT_ROOT / "docs"

####################################
# Data Collection
####################################

# This is going to be updated as I work
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/137.0 Safari/537.36"
    )
}

REQUEST_DELAY = 1.5  # Delay in seconds between requests to avoid rate limiting

##################################
# Study Parameters
##################################

START_YEAR = 2018
END_YEAR = 2025