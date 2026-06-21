"""
simulate.py — End-to-end simulation of the alert pipeline

Injects a fake NWS tornado warning for a given county and runs it through
the Phase 1 + Phase 2 logic to verify the watch-set matching works correctly
before we build the real scheduler in Phase 3.
"""

from datetime import datetime, timezone, timedelta
from adjacency import load_adjacency, get_watch_counties
from nws import TornadoWarning

# --- Config -----------------------------------------------------------
HOME_FIPS = "29189"   # St. Louis County, MO

# --- Build the watch set (Phase 1) ------------------------------------
print("=" * 55)
print("PHASE 1 — Loading adjacency data")
print("=" * 55)
adj = load_adjacency()
watch = get_watch_counties(HOME_FIPS, adj)
print(f"Home county : {HOME_FIPS} (St. Louis County, MO)")
print(f"Watch set   : {sorted(watch)}")
print(f"Total       : {len(watch)} counties\n")

# --- Inject a fake warning (Phase 2 stand-in) -------------------------
print("=" * 55)
print("PHASE 2 — Simulated NWS alert received")
print("=" * 55)

now = datetime.now(timezone.utc)

fake_warning = TornadoWarning(
    alert_id="urn:oid:SIMULATED.001",
    event="Tornado Warning",
    area_desc="Jefferson County, MO",
    county_fips={"29099"},   # Jefferson County FIPS
    sent=now,
    expires=now + timedelta(hours=1),
    severity="Extreme",
    headline="TORNADO WARNING issued for Jefferson County until 10:00 PM CDT",
)

print(f"Alert ID    : {fake_warning.alert_id}")
print(f"Event       : {fake_warning.event}")
print(f"Area        : {fake_warning.area_desc}")
print(f"FIPS codes  : {sorted(fake_warning.county_fips)}")
print(f"Severity    : {fake_warning.severity}")
print(f"Sent        : {fake_warning.sent.strftime('%Y-%m-%d %H:%M UTC')}")
print(f"Expires     : {fake_warning.expires.strftime('%Y-%m-%d %H:%M UTC')}\n")

# --- Alert filter (preview of Phase 3 logic) --------------------------
print("=" * 55)
print("PHASE 3 — Alert filter")
print("=" * 55)

matched = fake_warning.county_fips & watch   # set intersection

if matched:
    matched_fips = sorted(matched)
    is_home = HOME_FIPS in matched
    print(f"⚠️  MATCH FOUND — {len(matched)} warned county in your watch set")
    for fips in matched_fips:
        label = "(HOME COUNTY)" if fips == HOME_FIPS else "(ADJACENT COUNTY)"
        print(f"   {fips} {label}")
    print()
    print("📣 ALERT WOULD FIRE:")
    print(f"   {fake_warning.headline}")
    print()

    # Fire the real notifier so we can test the full pipeline end-to-end
    print("Sending push notification via ntfy.sh...")
    from notify import send_alert
    send_alert(fake_warning, set(matched_fips), is_home)
    print("Done — check your phone.")
else:
    print("✅ No match — warned counties are outside your watch set. No alert.")
