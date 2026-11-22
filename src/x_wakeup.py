"""Schedule X delivery using only its durable queue and publication date."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from .edge_state import Transport, location
from .x_queue import Settings, has_work, halted, load, normalize_stamp
from .x_switch import effective_enabled


def next_wakeup(state: dict, feed: dict, now: datetime, settings: Settings, *, guard=False) -> dict | None:
    local = now.astimezone(settings.tz)
    day = local.date().isoformat()
    end = datetime.combine(local.date(), settings.window_end, settings.tz)
    start = datetime.combine(local.date(), settings.expected_publish, settings.tz)
    if feed.get("date") != day or feed.get("timezone") != settings.timezone or not start <= local <= end:
        return None

    immediate = has_work(state, now, settings, feed_date=day,
                         feed_updated_at=normalize_stamp(feed.get("updated_at")))
    if immediate:
        # Protect a running job or a transient publication/proof failure;
        # the Worker independently checks the durable queue on wakeup.
        at = now + timedelta(minutes=10)
        end = min(end, now + timedelta(minutes=55))
    elif guard:
        return None
    else:
        edition = state["editions"].get(day)
        if not edition or edition["status"] != "active":
            return None
        jobs = [job for job in edition["jobs"] if job["status"] == "planned"
                and job["due_at"] and job["deadline"] and not halted(edition, job["language"])]
        if not jobs:
            return None
        first = min(jobs, key=lambda job: datetime.fromisoformat(job["due_at"]))
        at = datetime.fromisoformat(first["due_at"])
        end = min(end, datetime.fromisoformat(first["deadline"]))
    if at > end:
        return None
    return {"at": int(at.timestamp() * 1000), "deadline": int(end.timestamp() * 1000)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--feed-state", type=Path, required=True)
    parser.add_argument("--guard", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    delivery = config.get("x_delivery") or {}
    state = load(args.queue)
    feed = json.loads(args.feed_state.read_text())
    zone = config["filtering"]["daily_timezone"]
    settings = Settings.from_mapping(delivery, zone)
    due = None
    if effective_enabled(delivery.get("enabled")) and delivery.get("mode") == "drip":
        due = next_wakeup(state, feed, datetime.now(timezone.utc), settings, guard=args.guard)
    if args.guard and due is None:
        return
    lease = json.loads((location() / "lease.json").read_text())
    result = Transport().call("schedule-x", {"owner": lease["owner"], "wakeup": due, "guard": args.guard})
    acceptable = isinstance(result.get("scheduled"), int) if args.guard else result.get("scheduled", -1) == (due["at"] if due else None)
    if not acceptable:
        raise RuntimeError("X wakeup was not confirmed")
    print("X queue wakeup " + ("scheduled" if due else "cleared"))


if __name__ == "__main__":
    main()
