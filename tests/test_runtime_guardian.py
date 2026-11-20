from ops.runtime.guardian import decide
from ops.runtime.install import inject
import pytest


def test_guardian_never_restarts_active_busy_or_paused():
    for state, busy, paused in [("active", False, False), ("inactive", True, False), ("failed", False, True)]:
        assert not decide(state, busy, paused, [], 100000)[0]
    assert decide("failed", False, False, [], 100000)[0]
    assert not decide("failed", False, False, [99900], 100000)[0]
    assert not decide("failed", False, False, [90000, 93000, 96000], 100000)[0]
    assert decide("failed", False, False, [1000], 100000)[0]


def test_nginx_targeted_idempotent_injection():
    unrelated = "server { listen 443 ssl; server_name old.example; location / { return 404; } }"
    new = "server { listen 443 ssl; server_name api.xiyu.news; location /api/ { proxy_pass http://127.0.0.1:8080; } }"
    result = inject(unrelated + new)
    assert result.startswith(unrelated)
    assert inject(result) == result
    assert result.count("location = /ops/runtime.json") == 1
    with pytest.raises(ValueError):
        inject(unrelated)
