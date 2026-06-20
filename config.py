"""
config.py — Central configuration for storm_is_coming_app

Keep all magic numbers and user-specific settings here so monitor.py
stays clean. When we add notifications in Phase 4, those credentials
will live here too (loaded from environment variables, not hardcoded).
"""

# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------

# 5-digit FIPS code for your home county.
# St. Louis County, MO = 29189
# Look yours up at: https://www.census.gov/library/reference/code-lists/ansi.html
HOME_FIPS: str = "29189"
HOME_COUNTY_NAME: str = "St. Louis County, MO"

# ---------------------------------------------------------------------------
# Polling
# ---------------------------------------------------------------------------

# How often (in seconds) to poll the NWS API.
# NWS asks that you not poll faster than once per minute.
# Tornado warnings are issued with ~10-15 min lead time, so 3 min is plenty.
POLL_INTERVAL_SECONDS: int = 180

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
ADJACENCY_FILE = DATA_DIR / "county_adjacency.txt"
LOG_FILE = Path(__file__).parent / "monitor.log"
