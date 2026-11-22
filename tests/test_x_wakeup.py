from copy import deepcopy
from datetime import datetime, timedelta, timezone

from src.x_queue import Settings
from src.x_wakeup import next_wakeup

NOW = datetime(2026, 11, 22, 1, tzinfo=timezone.utc)
DAY = "2026-11-22"
SETTINGS = Settings()
FEED = {"date": DAY, "timezone": "Asia/Shanghai", "updated_at": NOW.isoformat()}
DUE = NOW + timedelta(hours=3)
DEADLINE = NOW + timedelta(hours=9)
QUEUED = {"editions": {DAY: {"status": "active", "state_updated_at": NOW.isoformat(), "jobs": [
    {"status": "sent", "slot": 1, "language": "zh", "due_at": NOW.isoformat(), "deadline": DEADLINE.isoformat()},
    {"status": "planned", "slot": 2, "language": "zh", "due_at": DUE.isoformat(), "deadline": DEADLINE.isoformat()},
]}}}


def test_arms_exact_due_time_without_a_polling_workflow():
    assert next_wakeup(QUEUED, FEED, NOW, SETTINGS) == {
        "at": int(DUE.timestamp() * 1000), "deadline": int(DEADLINE.timestamp() * 1000),
    }
    assert next_wakeup(QUEUED, FEED, NOW, SETTINGS, guard=True) is None


def test_new_edition_is_guarded_and_empty_or_stale_queues_do_not_wake():
    guard = next_wakeup({"editions": {}}, FEED, NOW, SETTINGS, guard=True)
    assert guard["at"] == int((NOW + timedelta(minutes=10)).timestamp() * 1000)
    sent = deepcopy(QUEUED)
    sent["editions"][DAY]["jobs"][1]["status"] = "sent"
    assert next_wakeup(sent, FEED, NOW, SETTINGS) is None
    assert next_wakeup(QUEUED, FEED, NOW + timedelta(days=1), SETTINGS) is None
