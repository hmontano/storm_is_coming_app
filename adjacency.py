"""
adjacency.py — County adjacency loader

Parses the Census Bureau county adjacency file and builds a lookup structure
that maps any county FIPS code to the set of its neighboring FIPS codes.

The raw file format is tab-delimited with a quirky structure:
  - A "header" row has 4 columns: county name, FIPS, neighbor name, neighbor FIPS
  - Subsequent rows for that county have only the last 2 columns (neighbor name, neighbor FIPS),
    with the first two columns empty.

This is essentially a run-length encoded format — we accumulate neighbors
until the next non-empty county name appears. Same pattern you'd see in
a ragged/hierarchical flat file from legacy systems.

Data source: https://www2.census.gov/geo/docs/reference/county_adjacency.txt
"""

from pathlib import Path
from collections import defaultdict


# Default path — sits next to this file in the data/ subdirectory
_DEFAULT_DATA_PATH = Path(__file__).parent / "data" / "county_adjacency.txt"


def load_adjacency(filepath: Path = _DEFAULT_DATA_PATH) -> dict[str, set[str]]:
    """
    Parse the Census adjacency file into a dict mapping each county FIPS
    to the set of all adjacent county FIPS codes (neighbors only, not self).

    Args:
        filepath: Path to the county_adjacency.txt file.

    Returns:
        A dict like {"29189": {"29071", "29099", ...}, ...}
    """
    adjacency: dict[str, set[str]] = defaultdict(set)
    current_fips: str | None = None

    with open(filepath, encoding="latin-1") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")

            # Strip surrounding quotes from name fields
            cols = [p.strip().strip('"') for p in parts]

            # A "header" row for a new county has content in columns 0 and 1.
            # The Census file has 4 tab-separated columns; when col 0 is non-empty
            # it's the start of a new county block.
            if cols[0]:
                # cols = [county_name, county_fips, neighbor_name, neighbor_fips]
                current_fips = cols[1].strip()
                neighbor_fips = cols[3].strip()
            else:
                # Continuation row — cols = ["", "", neighbor_name, neighbor_fips]
                neighbor_fips = cols[3].strip() if len(cols) >= 4 else ""

            # The first neighbor listed is always the county itself (FIPS == FIPS).
            # We skip self-references so the result set contains only true neighbors.
            if current_fips and neighbor_fips and neighbor_fips != current_fips:
                adjacency[current_fips].add(neighbor_fips)

    return dict(adjacency)


def get_watch_counties(home_fips: str, adjacency: dict[str, set[str]]) -> set[str]:
    """
    Return the full watch set: home county + all its immediate neighbors.

    This is the set we'll check against active NWS warnings. A tornado warning
    in any county in this set should trigger an alert.

    Args:
        home_fips: 5-digit FIPS code for your home county (e.g. "29189").
        adjacency: The dict returned by load_adjacency().

    Returns:
        A set of FIPS codes — home county plus all adjacent counties.
    """
    neighbors = adjacency.get(home_fips, set())
    return {home_fips} | neighbors


if __name__ == "__main__":
    # Quick smoke test — run this directly to verify the data loaded correctly.
    # St. Louis County, MO = 29189
    HOME_FIPS = "29189"

    print("Loading adjacency data...")
    adj = load_adjacency()
    print(f"Loaded {len(adj):,} counties.\n")

    watch = get_watch_counties(HOME_FIPS, adj)

    # Pull county names for readable output by inverting the file once more
    fips_to_name: dict[str, str] = {}
    with open(_DEFAULT_DATA_PATH, encoding="latin-1") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            cols = [p.strip().strip('"') for p in parts]
            if cols[0] and len(cols) >= 4:
                fips_to_name[cols[1].strip()] = cols[0]
                fips_to_name[cols[3].strip()] = cols[2]

    print(f"Watch set for FIPS {HOME_FIPS} ({fips_to_name.get(HOME_FIPS, 'Unknown')}):")
    print(f"  {len(watch)} counties total (home + {len(watch) - 1} neighbors)\n")
    for fips in sorted(watch):
        marker = " ← home" if fips == HOME_FIPS else ""
        print(f"  {fips}  {fips_to_name.get(fips, 'Unknown')}{marker}")
