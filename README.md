# Storm Is Coming App

Tornado warning alerter that notifies you when a warning is issued for your home county **or any adjacent county**.

## How It Works

1. **Adjacency layer** (`adjacency.py`) — loads the Census Bureau county adjacency file and builds a watch set: your home county + all immediate neighbors.
2. **NWS poller** (`nws.py`, Phase 2) — polls `api.weather.gov` every few minutes for active tornado warnings.
3. **Alert filter** (`monitor.py`, Phase 3) — checks if any warned county is in your watch set.
4. **Notifier** (`notify.py`, Phase 4) — sends a push notification / SMS when a match is found.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Data

`data/county_adjacency.txt` — Downloaded from the [Census Bureau](https://www2.census.gov/geo/docs/reference/county_adjacency.txt). Static file, update annually if needed.

## Phase 1 Smoke Test

```bash
python adjacency.py
```

Expected output: your home county + neighbors listed by FIPS code.

## County FIPS Reference

- St. Louis County, MO: `29189`
- Find any county: https://www.census.gov/library/reference/code-lists/ansi.html
