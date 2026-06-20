"""
nws.py — NWS Active Alert Poller

Fetches active tornado warnings from the NOAA/NWS public REST API and
returns a cleaned list of alert objects, each with the affected county
FIPS codes extracted and ready for comparison against our watch set.

API docs: https://www.weather.gov/documentation/services-web-api
Endpoint: GET https://api.weather.gov/alerts/active?event=Tornado%20Warning

The response is GeoJSON (FeatureCollection). Each feature's properties
contain a `geocode.SAME` list of 6-digit FIPS codes for affected counties.
No API key required — this is a public government service.

Rate limit: NWS asks for a descriptive User-Agent header and recommends
polling no faster than once per minute. We'll poll every 2–3 minutes.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

# NWS asks that you identify your app and provide contact info in the User-Agent.
# This is their soft rate-limit mechanism — no key needed, just be a good citizen.
_USER_AGENT = "storm_is_coming_app/0.1 (github.com/your-handle/storm_is_coming_app)"

_NWS_ALERTS_URL = "https://api.weather.gov/alerts/active"

# We only care about actual warnings, not tests or exercises.
_VALID_STATUSES = {"Actual"}


@dataclass
class TornadoWarning:
    """
    A cleaned, minimal representation of a single NWS tornado warning alert.

    We strip the raw GeoJSON down to just what we need for the alert filter
    in Phase 3 — this is the "data transfer object" (DTO) pattern: transform
    the external API shape into your own internal shape at the boundary.
    """

    alert_id: str                        # Unique NWS alert identifier (used for dedup)
    event: str                           # e.g. "Tornado Warning"
    area_desc: str                       # Human-readable area description
    county_fips: set[str]                # 6-digit FIPS codes from geocode.SAME
    sent: datetime                       # When the alert was issued
    expires: datetime                    # When the alert expires
    severity: str                        # "Extreme", "Severe", etc.
    headline: str = ""                   # Short headline if available


def get_active_tornado_warnings() -> list[TornadoWarning]:
    """
    Poll the NWS API for all currently active Tornado Warnings.

    Returns a list of TornadoWarning objects. Returns an empty list if
    there are no active warnings or if the API call fails (fail-safe: we
    don't want a network hiccup to crash the monitoring loop).
    """
    params = {"event": "Tornado Warning"}
    headers = {"User-Agent": _USER_AGENT, "Accept": "application/geo+json"}

    try:
        response = httpx.get(_NWS_ALERTS_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
    except httpx.TimeoutException:
        logger.warning("NWS API request timed out.")
        return []
    except httpx.HTTPStatusError as e:
        logger.error("NWS API returned HTTP %s: %s", e.response.status_code, e.response.text)
        return []
    except httpx.RequestError as e:
        logger.error("NWS API request failed: %s", e)
        return []

    data = response.json()
    features = data.get("features", [])

    warnings: list[TornadoWarning] = []
    for feature in features:
        warning = _parse_feature(feature)
        if warning:
            warnings.append(warning)

    logger.info("NWS poll complete — %d active tornado warning(s) found.", len(warnings))
    return warnings


def _parse_feature(feature: dict) -> TornadoWarning | None:
    """
    Parse a single GeoJSON feature into a TornadoWarning.

    Returns None if the alert is not 'Actual' status (filters out test
    and exercise messages that NWS occasionally broadcasts).
    """
    props = feature.get("properties", {})

    # Skip non-actual messages (tests, exercises, system messages)
    if props.get("status") not in _VALID_STATUSES:
        return None

    # geocode.SAME holds 6-digit FIPS codes — this is the field we match
    # against the Census adjacency watch set. The leading zero matters for
    # states like Missouri (29xxx) — keep them as strings, never cast to int.
    same_codes: list[str] = props.get("geocode", {}).get("SAME", [])
    county_fips = set(same_codes)

    # Parse ISO 8601 timestamps — NWS always includes timezone offset
    sent = _parse_dt(props.get("sent", ""))
    expires = _parse_dt(props.get("expires", ""))

    return TornadoWarning(
        alert_id=props.get("id", ""),
        event=props.get("event", ""),
        area_desc=props.get("areaDesc", ""),
        county_fips=county_fips,
        sent=sent,
        expires=expires,
        severity=props.get("severity", ""),
        headline=props.get("parameters", {}).get("NWSheadline", [""])[0],
    )


def _parse_dt(dt_str: str) -> datetime:
    """Parse an ISO 8601 datetime string from NWS into a datetime object."""
    if not dt_str:
        return datetime.min
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        logger.warning("Could not parse datetime string: %s", dt_str)
        return datetime.min


if __name__ == "__main__":
    # Smoke test — run directly to check the API is reachable and parseable.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("Polling NWS for active Tornado Warnings...\n")
    warnings = get_active_tornado_warnings()

    if not warnings:
        print("No active tornado warnings at this time.")
    else:
        for w in warnings:
            print(f"[{w.severity}] {w.event}")
            print(f"  ID:      {w.alert_id}")
            print(f"  Area:    {w.area_desc}")
            print(f"  FIPS:    {sorted(w.county_fips)}")
            print(f"  Sent:    {w.sent}")
            print(f"  Expires: {w.expires}")
            print()
