# Storm Is Coming App

Tornado warning alerter that notifies you when a warning is issued for your home county **or any adjacent county**.

## How It Works

1. **Adjacency layer** (`adjacency.py`) — loads the Census Bureau county adjacency file and builds a watch set: your home county + all immediate neighbors.
2. **NWS poller** (`nws.py`) — polls `api.weather.gov` every 3 minutes for active tornado warnings.
3. **Alert filter** (`monitor.py`) — checks if any warned county is in your watch set.
4. **Notifier** (`notify.py`) — sends a push notification via ntfy.sh when a match is found.
5. **Service** (`storm-monitor.service`) — runs the monitor as a persistent systemd user service.

## Setup

```bash
python3 -m venv .venv-storm
source .venv-storm/bin/activate
pip install -r requirements.txt
```

Create a `.env` file from the example:
```bash
cp .env.example .env
# Edit .env and set your NTFY_TOPIC
```

## Running as a Persistent Service (systemd)

```bash
mkdir -p ~/.config/systemd/user
cp storm-monitor.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable storm-monitor
systemctl --user start storm-monitor

# Allow service to run after logout/reboot
loginctl enable-linger $USER
```

Useful commands:
```bash
# Check status
systemctl --user status storm-monitor

# View live logs
journalctl --user -u storm-monitor -f

# Stop the service
systemctl --user stop storm-monitor

# Restart after code changes
systemctl --user restart storm-monitor
```

## Running Manually

```bash
source .venv-storm/bin/activate
python monitor.py
```

## Simulation / Testing

```bash
python simulate.py
```

Fires a fake warning for a configurable county and sends a real ntfy.sh notification. Edit `simulate.py` to test different counties.

## Data

`data/county_adjacency.txt` — Downloaded from the [Census Bureau](https://www2.census.gov/geo/docs/reference/county_adjacency.txt). Static file, update annually if needed.

## County FIPS Reference

- St. Louis County, MO: `29189`
- Find any county: https://www.census.gov/library/reference/code-lists/ansi.html
