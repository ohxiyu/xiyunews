"""Offline guards for the opt-in production deployment and its toolchain."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_final_cutover_preserves_namespace_by_transfer_not_creation():
    text = (ROOT / "ops/daily-dispatcher/wrangler.unified.jsonc").read_text()
    config = json.loads(re.sub(r"^\s*//.*$", "", text, flags=re.M))
    assert config["name"] == "xiyunews"
    assert config["durable_objects"]["bindings"] == [{"name": "RECOVERY_GATE", "class_name": "RecoveryGate"}]
    assert config["migrations"] == [{"tag": "xiyunews-recovery-transfer-20261003",
        "transferred_classes": [{"from": "RecoveryGate", "from_script": "bmtnews-daily-dispatcher", "to": "RecoveryGate"}]}]
    assert "new_classes" not in text and "new_sqlite_classes" not in text and "deleted_classes" not in text
    assert config["kv_namespaces"] == [{"binding": "STATE", "id": "469346950dfc4f36b8d9bf9997d960fa"}]
    assert config["triggers"]["crons"] == ["26 23 * * *", "36,46,56 23 * * *", "*/5 * * * *"]
    assert config["routes"] == [{"pattern": "xiyu.news", "custom_domain": True}]
    assert config["vars"]["ENABLE_DISPATCHER"] == "true"
    assert config["vars"]["ENABLE_REALTIME_WATCHDOG"] == "true"


def test_edge_deployment_requires_main_and_audits_before_upload():
    workflow = (ROOT / ".github/workflows/cloudflare-unified.yml").read_text()
    assert "vars.XIYUNEWS_EDGE_ENABLED == 'true'" in workflow
    assert "github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main'" in workflow
    assert "github.event.workflow_run.conclusion == 'success'" in workflow
    assert "github.event.workflow_run.head_branch == 'main'" in workflow
    assert "github.event.workflow_run.head_repository.full_name == github.repository" in workflow
    assert workflow.index("run: npm ci") < workflow.index("run: npm run audit")
    assert workflow.index("run: npm run audit") < workflow.index("npx wrangler deploy")


def test_deployment_does_not_require_an_unconfigured_paid_environment():
    workflow = (ROOT / ".github/workflows/cloudflare-unified.yml").read_text()
    assert "environment: xiyunews-production" not in workflow
    assert "CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}" in workflow
    assert "CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}" in workflow


def test_dependency_audit_includes_the_locked_development_toolchain():
    dispatcher = ROOT / "ops/daily-dispatcher"
    package = json.loads((dispatcher / "package.json").read_text())
    lock = json.loads((dispatcher / "package-lock.json").read_text())
    assert package["scripts"]["audit"] == "npm audit --audit-level=low"
    assert package["scripts"]["check"].startswith("npm run audit && ")
    assert package["devDependencies"] == lock["packages"][""]["devDependencies"]
    for name, version in package["overrides"].items():
        resolved = [item for path, item in lock["packages"].items()
                    if path.endswith(f"node_modules/{name}")]
        assert resolved, f"override {name} must resolve in the lockfile"
        assert all(item["version"] == version for item in resolved)
