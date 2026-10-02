#!/usr/bin/env python3
"""Watch Google Calendar guests' RSVP status and print ONLY on change.

Designed as a Hermes cron watchdog (no_agent=True): empty stdout => no message.
First run only establishes a baseline (silent).

Usage:  python3 rsvp_watch.py            # normal
        python3 rsvp_watch.py --reset    # wipe baseline and re-baseline silently
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from pathlib import Path

SCRIPTS = Path.home() / ".hermes" / "skills" / "productivity" / "google-workspace" / "scripts"
sys.path.insert(0, str(SCRIPTS))

# Token guard
TOKEN_PATH = Path.home() / ".hermes" / "google_token.json"
if not TOKEN_PATH.exists():
    sys.exit(0)

try:
    import google_api as g  # noqa: E402
except ImportError:
    sys.exit(0)

STATE_PATH = Path.home() / ".hermes" / "state" / "rsvp_watch.json"
FAIL_PATH = Path.home() / ".hermes" / "state" / "rsvp_watch_failures.json"
WINDOW_BACK_DAYS = 2
WINDOW_FWD_DAYS = 45
RETRIES = 2
RETRY_SLEEP = 3

EMOJI = {
    "accepted": "✅",
    "declined": "❌",
    "tentative": "❓",
    "needsAction": "⏳",
}
LABEL = {
    "accepted": "accepted",
    "declined": "declined",
    "tentative": "maybe",
    "needsAction": "no reply yet",
}


def _fmt_when(raw: str) -> str:
    if not raw:
        return "(no date)"
    try:
        if "T" in raw:
            d = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return d.strftime("%a %d/%m %H:%M")
        return dt.date.fromisoformat(raw).strftime("%a %d/%m")
    except Exception:
        return raw


def _record_failure(err: Exception) -> int:
    FAIL_PATH.parent.mkdir(parents=True, exist_ok=True)
    count = 1
    try:
        if FAIL_PATH.exists():
            data = json.loads(FAIL_PATH.read_text())
            count = data.get("count", 0) + 1
    except Exception:
        count = 1
    FAIL_PATH.write_text(json.dumps({"count": count, "last_error": str(err)}))
    return count


def _clear_failures() -> None:
    try:
        if FAIL_PATH.exists():
            FAIL_PATH.unlink()
    except Exception:
        pass


def _collect_state(svc) -> dict[str, dict]:
    my_email = ""
    try:
        my_email = svc.calendars().get(calendarId="primary").execute().get("id", "")
    except Exception:
        pass

    now = dt.datetime.now(dt.timezone.utc)
    tmin = (now - dt.timedelta(days=WINDOW_BACK_DAYS)).isoformat()
    tmax = (now + dt.timedelta(days=WINDOW_FWD_DAYS)).isoformat()

    events_res = (
        svc.events()
        .list(
            calendarId="primary",
            timeMin=tmin,
            timeMax=tmax,
            singleEvents=True,
            orderBy="startTime",
            maxResults=250,
            fields="items(id,summary,start,attendees,organizer,status)",
        )
        .execute()
    )

    out: dict[str, dict] = {}
    for ev in events_res.get("items", []):
        if ev.get("status") == "cancelled":
            continue
        attendees = ev.get("attendees") or []
        if not attendees:
            continue
        eid = ev["id"]
        summary = ev.get("summary") or "(Untitled)"
        start_raw = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date") or ""
        when = _fmt_when(start_raw)

        for att in attendees:
            email = att.get("email") or ""
            if not email or att.get("self") or email.lower() == my_email.lower():
                continue
            key = f"{eid}::{email}"
            out[key] = {
                "event_id": eid,
                "summary": summary,
                "when": when,
                "email": email,
                "displayName": att.get("displayName") or email,
                "status": att.get("responseStatus") or "needsAction",
            }
    return out


def main() -> None:
    reset = "--reset" in sys.argv
    svc = None
    last_err: Exception | None = None

    for attempt in range(RETRIES):
        try:
            svc = g.build_service("calendar", "v3")
            current = _collect_state(svc)
            break
        except Exception as exc:
            last_err = exc
            if attempt < RETRIES - 1:
                time.sleep(RETRY_SLEEP)
    else:
        fails = _record_failure(last_err or Exception("Unknown error"))
        if fails >= 2:
            print(f"⚠️ Calendar RSVP watch failed: {type(last_err).__name__}: {last_err}")
        return

    _clear_failures()

    old: dict[str, dict] = {}
    if not reset and STATE_PATH.exists():
        try:
            old = json.loads(STATE_PATH.read_text())
        except Exception:
            old = {}

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(current, indent=2))

    if reset or not old:
        return

    lines = []
    for key, cur in current.items():
        prev = old.get(key)
        if not prev:
            continue
        if prev.get("status") != cur["status"]:
            who = cur.get("displayName") or cur["email"]
            old_s = prev.get("status", "needsAction")
            new_s = cur["status"]
            icon = EMOJI.get(new_s, "ℹ️")
            lines.append(
                f"{icon} **{who}** {LABEL.get(new_s, new_s)} (was {LABEL.get(old_s, old_s)}): "
                f"\"{cur['summary']}\" ({cur['when']})"
            )

    if lines:
        print("🔔 **RSVP status update:**")
        for line in lines:
            print(line)


if __name__ == "__main__":
    main()
