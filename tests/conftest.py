import os

import pytest

os.environ.setdefault("TELEGRAM_ENABLED", "false")


@pytest.fixture(autouse=True)
def no_digest_hold(monkeypatch):
    """Existing delivery tests claim immediately; digest tests set the hold explicitly."""
    from src.platform.store import Store

    original = Store.__init__

    def init(self, path):
        original(self, path)
        self.policy["digest"]["hold_seconds"] = 0

    monkeypatch.setattr(Store, "__init__", init)
