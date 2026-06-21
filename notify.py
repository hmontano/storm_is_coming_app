"""
notify.py — Notification dispatcher

Sends push notifications via ntfy.sh when a tornado warning matches
the watch set. Called from monitor._fire_alert() as the Phase 4 seam.

ntfy.sh is a free, open-source push notification service. You subscribe
to a topic in the ntfy phone app and this module POSTs to that topic.
No account required for basic use — topic name is the only "credential".

Docs: https://docs.ntfy.sh/publish/
"""

import logging
import os

import httpx
from dotenv import load_dotenv

from nws import TornadoWarning

load_dotenv()

logger = logging.getLogger(__name__)

_NTFY_BASE_URL = "https://ntfy.sh"

# ntfy priority levels — these map to how aggressively the app
# interrupts you (sound, vibration, Do Not Disturb bypass).
# https://docs.ntfy.sh/publish/#message-priority
_PRIORITY_HOME     = "max"    # Home county — sirens-going-off urgency
_PRIORITY_ADJACENT = "urgent" # Adjacent county — important but not immediate


def send_alert(warning: TornadoWarning, matched_fips: set[str], is_home: bool) -> None:
    """
    Send a push notification for a matched tornado warning.

    Args:
        warning:      The matched TornadoWarning object from the NWS poller.
        matched_fips: The FIPS codes that triggered the match (subset of watch set).
        is_home:      True if the home county itself is under the warning.
    """
    topic = os.getenv("NTFY_TOPIC")
    if not topic:
        logger.error("NTFY_TOPIC not set in .env — cannot send notification.")
        return

    title, body, priority = _build_message(warning, matched_fips, is_home)

    try:
        response = httpx.post(
            f"{_NTFY_BASE_URL}/{topic}",
            content=body.encode("utf-8"),
            headers={
                "Title": title,
                "Priority": priority,
                "Tags": "rotating_light,tornado",
            },
            timeout=10,
        )
        response.raise_for_status()
        logger.info("Notification sent via ntfy.sh (priority=%s).", priority)
    except httpx.HTTPStatusError as e:
        logger.error("ntfy.sh returned HTTP %s: %s", e.response.status_code, e.response.text)
    except httpx.RequestError as e:
        logger.error("Failed to reach ntfy.sh: %s", e)


def _build_message(
    warning: TornadoWarning,
    matched_fips: set[str],
    is_home: bool,
) -> tuple[str, str, str]:
    """
    Build the notification title, body, and priority level.

    Returns a (title, body, priority) tuple. Keeping message construction
    separate from the HTTP call makes it easy to unit test later.
    """
    if is_home:
        title = "Tornado Warning - YOUR COUNTY"
        priority = _PRIORITY_HOME
    else:
        title = "Tornado Warning - Nearby County"
        priority = _PRIORITY_ADJACENT

    expires_str = warning.expires.strftime("%I:%M %p %Z").lstrip("0")

    body_lines = [
        warning.area_desc,
        f"Expires: {expires_str}",
    ]
    if warning.headline:
        body_lines.append(warning.headline)

    return title, "\n".join(body_lines), priority
