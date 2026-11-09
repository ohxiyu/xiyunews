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
        "cloudflare-unified.yml": 30,
        "feed-collection.yml": 30,
    }

    for workflow_name, limit in expected_limits.items():
        assert (
            f"timeout-minutes: {limit}" in _workflow(workflow_name)
        ), workflow_name




def test_single_deployment_renders_without_collection_ai_or_channel_messages():
    deploy = _workflow("cloudflare-unified.yml")
    assert "ref: gh-pages" in deploy
    assert "python -m src.core_site --root .edge-source" in deploy
    assert "SILICONFLOW_API_KEY" not in deploy
    assert "src.core_delivery" not in deploy
    assert "scripts/verify_daily_deployment.py" in deploy
    assert "production-edition" in deploy
    assert {p.name for p in WORKFLOWS.glob("*.yml")} == {
        "ci.yml", "codeql.yml", "server-backup.yml", "feed-collection.yml",
        "daily-summary.yml", "daily-telegram.yml", "x-distribution.yml", "cloudflare-unified.yml"}
