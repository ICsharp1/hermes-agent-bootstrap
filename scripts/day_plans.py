#!/usr/bin/env python3
"""Morning/evening plan check for Google Calendar.

Runs hourly from cron (no_agent): prints ONLY when there is something to say, so
an empty stdout sends no message at all.

  * at 07:00 local time -> "do I have plans this evening?" (today 16:00-23:59)
  * at 22:00 local time -> "do I have plans tomorrow morning?" (tomorrow 00:00-12:00)

Any other hour: silent. Local-hour check is handled in code rather than cron schedule
so the job stays aligned across Daylight Saving Time shifts.
"""
from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

# Timezone resolution
TZ_NAME = os.environ.get("HERMES_TIMEZONE", "Asia/Jerusalem")
try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo(TZ_NAME)
except Exception:
    LOCAL_TZ = dt.timezone.utc

SCRIPTS = Path.home() / ".hermes" / "skills" / "productivity" / "google-workspace" / "scripts"
sys.path.insert(0, str(SCRIPTS))

# Token existence guard: if calendar is not yet authenticated, stay silent
TOKEN_PATH = Path.home() / ".hermes" / "google_token.json"
if not TOKEN_PATH.exists():
    sys.exit(0)

try:
    import google_api as g  # noqa: E402
except ImportError:
    sys.exit(0)

MORNING_HOUR = int(os.environ.get("HERMES_PLAN_MORNING_HOUR", "7"))
NIGHT_HOUR = int(os.environ.get("HERMES_PLAN_NIGHT_HOUR", "22"))
EVENING_FROM = 16
MORNING_TO = 12

# Optional marker for shared calendars (e.g. if events on a team calendar must contain your name)
USER_MARKER = os.environ.get("HERMES_CALENDAR_USER_MARKER", "").strip()


def _writable_calendars(svc):
    items = svc.calendarList().list(maxResults=250).execute().get("items", [])
    return [c for c in items if c.get("accessRole") in ("owner", "writer")]


def _is_mine(cal: dict, summary: str) -> bool:
    if cal.get("primary"):
        return True
    if not USER_MARKER:
        return True
    return USER_MARKER.casefold() in (summary or "").casefold()


def _fmt(ev: dict) -> tuple[str, str]:
    start = ev.get("start", {})
    if "date" in start:
        return "All Day", ev.get("summary") or "(Untitled)"
    raw = start.get("dateTime", "")
    try:
        local = dt.datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(LOCAL_TZ)
        when = local.strftime("%H:%M")
    except Exception:
        when = raw
    return when, ev.get("summary") or "(Untitled)"


def collect(svc, tmin: dt.datetime, tmax: dt.datetime) -> list[str]:
    rows: list[tuple[dt.datetime, str, str, str]] = []
    for cal in _writable_calendars(svc):
        try:
            items = (
                svc.events()
                .list(
                    calendarId=cal["id"],
                    timeMin=tmin.isoformat(),
                    timeMax=tmax.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=100,
                    fields="items(summary,start,status)",
                )
                .execute()
                .get("items", [])
            )
        except Exception:
            continue
        for ev in items:
            if ev.get("status") == "cancelled":
                continue
            if not _is_mine(cal, ev.get("summary")):
                continue
            when, title = _fmt(ev)
            start = ev.get("start", {})
            if "date" in start:
                sort_key = dt.datetime.fromisoformat(start["date"]).replace(tzinfo=LOCAL_TZ)
                when = "All Day"
            else:
                sort_key = dt.datetime.fromisoformat(
                    start.get("dateTime", "").replace("Z", "+00:00")
                ).astimezone(LOCAL_TZ)
            rows.append((sort_key, when, title, cal.get("summary", "")))
    rows.sort(key=lambda r: r[0])
    return [f"{when} — {title}" for _, when, title, _ in rows]


def main() -> None:
    forced = None
    if "--at" in sys.argv:
        try:
            forced = int(sys.argv[sys.argv.index("--at") + 1])
        except Exception:
            forced = None

    now = dt.datetime.now(LOCAL_TZ)
    hour = forced if forced is not None else now.hour

    if hour == MORNING_HOUR:
        tmin = now.replace(hour=EVENING_FROM, minute=0, second=0, microsecond=0)
        tmax = now.replace(hour=23, minute=59, second=59, microsecond=0)
        header = "📅 Plans for this evening:"
    elif hour == NIGHT_HOUR:
        tomorrow = (now + dt.timedelta(days=1)).date()
        tmin = dt.datetime.combine(tomorrow, dt.time(0, 0), tzinfo=LOCAL_TZ)
        tmax = dt.datetime.combine(tomorrow, dt.time(MORNING_TO, 0), tzinfo=LOCAL_TZ)
        header = "📅 Plans for tomorrow morning:"
    else:
        return

    try:
        svc = g.build_service("calendar", "v3")
        lines = collect(svc, tmin, tmax)
    except Exception as exc:
        print(f"⚠️ Calendar check failed: {type(exc).__name__}: {exc}")
        return

    if not lines:
        return

    print(header)
    for line in lines[:12]:
        print("• " + line)


if __name__ == "__main__":
    main()
