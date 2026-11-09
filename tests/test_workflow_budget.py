from pathlib import Path


ROOT = Path(__file__).parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def _workflow(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_pr_checks_do_not_repeat_after_merge() -> None:
    ci = _workflow("ci.yml")
    codeql = _workflow("codeql.yml")

    assert "pull_request:" in ci
    assert "\n  push:" not in ci
    assert "group: ci-${{ github.event.pull_request.number || github.ref }}-${{ github.event_name }}" in ci
    assert "cancel-in-progress: true" in ci
    assert "npm run check" in ci
    assert "ops/daily-dispatcher" in ci

    assert "pull_request:" in codeql
    assert "\n  push:" not in codeql
    assert 'cron: "23 3 * * 1"' in codeql
    assert (
        "group: codeql-${{ github.event.pull_request.number || github.run_id }}"
        in codeql
    )
    assert "cancel-in-progress: true" in codeql


def test_all_hosted_jobs_have_bounded_runtime() -> None:
    expected_limits = {
        "ci.yml": 15,
        "codeql.yml": 15,
        "daily-summary.yml": 30,
        "deploy-docs.yml": 30,
        "feed-collection.yml": 30,
        "schedule-watchdog.yml": 10,
    }

    for workflow_name, limit in expected_limits.items():
        assert (
            f"timeout-minutes: {limit}" in _workflow(workflow_name)
        ), workflow_name




def test_docs_deploy_rebuilds_core_reader_without_entity_ai_or_messages():
    deploy = _workflow("deploy-docs.yml")
    assert "Checkout current published site" in deploy
    assert "Restore current published archive" in deploy
    assert "python -m src.core_site --root docs" in deploy
    assert "python -m src.entity_republish" not in deploy
    assert "python -m src.quick_posts" not in deploy
