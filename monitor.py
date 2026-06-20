"""
monitor.py — Alert monitor and scheduler

The main entry point for the app. Runs a scheduled polling loop that:
  1. Fetches active tornado warnings from the NWS API
  2. Checks if any warned county is in your watch set (home + neighbors)
  3. Fires an alert for new matches (deduped by alert ID)

Run with:
    python monitor.py

This is a long-running process — keep the terminal open or run it in a
screen/tmux session. Phase 5 will add proper daemonization.
"""

import logging
import signal
import sys
import time
from datetime import datetime, timezone

from apscheduler.schedulers.blocking import BlockingScheduler

import config
from adjacency import load_adjacency, get_watch_counties
from nws import TornadoWarning, get_active_tornado_warnings

# ---------------------------------------------------------------------------
# Logging — writes to both console and a log file
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.LOG_FILE),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# State — in-memory dedup set (see Phase 5 notes for persistence option)
# ---------------------------------------------------------------------------

# Holds alert IDs we've already fired on. A set gives us O(1) lookup,
# which matters when there are many simultaneous warnings during a major
# outbreak. IDs are strings like "urn:oid:2.49.0.1.840.0.abc123..."
seen_alert_ids: set[str] = set()

# Built once at startup, reused every poll cycle — no need to re-read
# the adjacency file on every tick.
watch_set: set[str] = set()


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def check_for_warnings() -> None:
    """
    Single poll cycle: fetch → filter → alert.

    Called by APScheduler on every tick. All exceptions are caught so a
    transient network error doesn't kill the scheduler process.
    """
    try:
        _run_check()
    except Exception as e:
        logger.error("Unexpected error during poll cycle: %s", e, exc_info=True)


def _run_check() -> None:
    """Inner logic, separated so exceptions propagate cleanly to the caller."""
    logger.info("Polling NWS for active Tornado Warnings...")
    warnings = get_active_tornado_warnings()

    if not warnings:
        logger.info("No active tornado warnings.")
        return

    logger.info("%d active warning(s) found — checking against watch set...", len(warnings))

    for warning in warnings:
        matched_fips = warning.county_fips & watch_set

        if not matched_fips:
            continue  # This warning doesn't affect our area

        if warning.alert_id in seen_alert_ids:
            logger.info("Already alerted for %s — skipping.", warning.alert_id)
            continue

        # New match — mark as seen and fire the alert
        seen_alert_ids.add(warning.alert_id)
        _fire_alert(warning, matched_fips)


def _fire_alert(warning: TornadoWarning, matched_fips: set[str]) -> None:
    """
    Handle a new, matched tornado warning.

    Right now this just logs the alert prominently. Phase 4 will call the
    notifier (ntfy/Twilio) from here — this function is the single seam
    where notification logic plugs in.
    """
    is_home = config.HOME_FIPS in matched_fips

    # Build a human-readable list of the matched counties
    county_label = "YOUR COUNTY" if is_home else "ADJACENT COUNTY"
    matched_list = ", ".join(sorted(matched_fips))

    # Separator makes it easy to spot alerts in the log
    logger.warning("=" * 60)
    logger.warning("⚠️  TORNADO WARNING ALERT")
    logger.warning("  Event    : %s", warning.event)
    logger.warning("  Severity : %s", warning.severity)
    logger.warning("  Match    : %s (%s)", matched_list, county_label)
    logger.warning("  Area     : %s", warning.area_desc)
    logger.warning("  Expires  : %s", warning.expires.strftime("%Y-%m-%d %H:%M %Z"))
    if warning.headline:
        logger.warning("  Headline : %s", warning.headline)
    logger.warning("=" * 60)

    # ---------------------------------------------------------------
    # Phase 4 hook — notifier call goes here, e.g.:
    #   from notify import send_alert
    #   send_alert(warning, matched_fips, is_home)
    # ---------------------------------------------------------------


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

def _build_watch_set() -> None:
    """Load adjacency data and populate the global watch set at startup."""
    global watch_set
    logger.info("Loading county adjacency data...")
    adj = load_adjacency(config.ADJACENCY_FILE)
    watch_set = get_watch_counties(config.HOME_FIPS, adj)
    logger.info(
        "Watch set ready — monitoring %d counties centered on %s.",
        len(watch_set),
        config.HOME_COUNTY_NAME,
    )
    logger.info("Watch set FIPS: %s", sorted(watch_set))


def _handle_shutdown(signum, frame) -> None:
    """Graceful shutdown on Ctrl+C or SIGTERM."""
    logger.info("Shutdown signal received — stopping monitor.")
    sys.exit(0)


def main() -> None:
    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    logger.info("Starting storm_is_coming_app monitor.")
    logger.info("Home county: %s (%s)", config.HOME_COUNTY_NAME, config.HOME_FIPS)
    logger.info("Poll interval: %ds", config.POLL_INTERVAL_SECONDS)

    _build_watch_set()

    # Run one immediate check so we don't wait a full interval on startup
    check_for_warnings()

    # APScheduler's BlockingScheduler runs in the main thread — the process
    # stays alive here until interrupted. Think of it like cron embedded in
    # your Python process: no system config, no crontab, just runs.
    scheduler = BlockingScheduler()
    scheduler.add_job(
        check_for_warnings,
        trigger="interval",
        seconds=config.POLL_INTERVAL_SECONDS,
        id="nws_poll",
        name="NWS Tornado Warning Poll",
    )

    logger.info("Scheduler started — polling every %ds. Press Ctrl+C to stop.\n", config.POLL_INTERVAL_SECONDS)
    scheduler.start()


if __name__ == "__main__":
    main()
