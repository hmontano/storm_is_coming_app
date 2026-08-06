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

### First-time install

```bash
mkdir -p ~/.config/systemd/user
cp storm-monitor.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable storm-monitor
systemctl --user start storm-monitor

# Allow service to run after logout/reboot
loginctl enable-linger $USER
```

### Starting and stopping

`systemctl` tracks two independent things: whether the service is **running right now**
(active/inactive) and whether it **starts automatically on login or reboot**
(enabled/disabled). Turning the monitor off or back on usually means setting both.

```bash
# Start now, and start automatically on every login/reboot
systemctl --user enable --now storm-monitor

# Stop now, and stay off across reboots
systemctl --user disable --now storm-monitor
```

If you only want to change one of the two:

```bash
systemctl --user start storm-monitor     # run now, don't change boot behavior
systemctl --user stop storm-monitor      # stop now, but it returns on reboot if enabled
systemctl --user enable storm-monitor    # run on boot, don't start now
systemctl --user disable storm-monitor   # don't run on boot, don't stop now
```

Pick up code changes without touching the enabled state:

```bash
systemctl --user restart storm-monitor
```

If you edited `storm-monitor.service` itself, copy it over and reload the unit
definitions first, otherwise systemd keeps using the old copy:

```bash
cp storm-monitor.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user restart storm-monitor
```

### Checking on it

```bash
# Is it running? Is it enabled?
systemctl --user status storm-monitor
systemctl --user is-active storm-monitor
systemctl --user is-enabled storm-monitor

# Follow live logs
journalctl --user -u storm-monitor -f

# Recent history, including runs from previous boots
journalctl --user -u storm-monitor --since "2 hours ago"
```

A healthy service logs a poll roughly every 3 minutes. If polls have stopped
appearing while the service still reports `active`, check the logs for repeated
`api.weather.gov` request failures.

> **Current state:** the monitor is stopped and disabled as of 2026-08-05, so **no
> tornado alerts are being sent**. Re-enable with
> `systemctl --user enable --now storm-monitor`.

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
