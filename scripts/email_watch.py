#!/usr/bin/env python3
"""Inbox watcher for the secondary/scout mailbox.

Designed as a Hermes cron `monitor`: output is DETERMINISTIC (no timestamps,
no random order) so identical ticks skip agent LLM runs entirely (zero token cost
when nothing changed).

Safety gate: if 20 or more new messages arrived since the last check, it does
not inspect their content — it reports overflow and stops, protecting against spam
token loss.

Usage: python3 email_watch.py            # normal
       python3 email_watch.py --reset    # forget seen state (re-baseline)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Scout token path
DEFAULT_TOKEN = Path.home() / ".hermes" / "google_token_scout.json"
token_file = os.environ.get("HERMES_GOOGLE_TOKEN", str(DEFAULT_TOKEN))
os.environ["HERMES_GOOGLE_TOKEN"] = token_file

# Token existence guard: if scout mailbox is not configured yet, exit cleanly
if not Path(token_file).exists():
    sys.exit(0)

SCRIPTS = Path.home() / ".hermes" / "skills" / "productivity" / "google-workspace" / "scripts"
sys.path.insert(0, str(SCRIPTS))

try:
    import google_api as g  # noqa: E402
except ImportError:
    sys.exit(0)

STATE_PATH = Path.home() / ".hermes" / "state" / "email_watch_seen.json"
MAX_NEW = 20
SHOW = 12
SCAN = 200
KEEP_SEEN = 1000


def load_seen() -> set[str]:
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return set(data.get("seen", []))
    except Exception:
        return set()


def save_seen(ids: list[str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"seen": ids[-KEEP_SEEN:]}
    STATE_PATH.write_text(json.dumps(payload), encoding="utf-8")


def main() -> None:
    try:
        svc = g.build_service("gmail", "v1")
        listing = (
            svc.users()
            .messages()
            .list(userId="me", q="in:inbox", maxResults=SCAN)
            .execute()
            .get("messages", [])
        )
    except Exception as exc:
        print(f"STATUS error {type(exc).__name__}")
        return

    seen = set() if "--reset" in sys.argv else load_seen()
    ids = [m["id"] for m in listing]
    new_ids = [i for i in ids if i not in seen]

    if len(new_ids) >= MAX_NEW:
        save_seen(ids)
        print("STATUS overflow")
        print(f"NEW {len(new_ids)}")
        return

    if not new_ids:
        save_seen(ids)
        print("STATUS ok")
        print("NEW 0")
        return

    rows = []
    for mid in new_ids[:SHOW]:
        try:
            full = (
                svc.users()
                .messages()
                .get(
                    userId="me",
                    id=mid,
                    format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                )
                .execute()
            )
            h = {x["name"]: x["value"] for x in full["payload"]["headers"]}
            unread = "UNREAD" if "UNREAD" in full.get("labelIds", []) else "read"
            rows.append(
                f"MSG {mid} | {unread} | {h.get('From', '?')[:60]} | {h.get('Subject', '?')[:90]}"
            )
        except Exception:
            rows.append(f"MSG {mid} | ? | ? | ?")

    save_seen(ids)
    print("STATUS ok")
    print(f"NEW {len(new_ids)}")
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
