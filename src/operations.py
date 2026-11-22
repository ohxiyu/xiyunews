"""Persist workflow outcomes and estimated AI costs to the publication state."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo


from ._file_utils import _atomic_write_text
from .publication_state import active_store

PRICE_SOURCE = 'https://docs.siliconflow.cn/docs/release-notes/overview'


def estimate_cost(rows):
    """CNY estimate at 2026-06-25 prices; reasoning is included in output."""
    total = Decimal(0)
    unpriced = 0
    for row in rows:
        if row.get('provider') != 'siliconflow' or row.get('model') != 'deepseek-ai/DeepSeek-V3.2':
            if row.get('calls') or row.get('input_tokens') or row.get('output_tokens'):
                unpriced += 1
            continue
        values = [row.get(k, 0) for k in ('input_tokens', 'output_tokens', 'cached_input_tokens')]
        if any(type(v) is not int or v < 0 for v in values):
            unpriced += 1
            continue
        incoming, outgoing, cached = values
        if cached > incoming:
            unpriced += 1
            continue
        total += (Decimal(incoming-cached)*4 + Decimal(cached)*Decimal('.4') + Decimal(outgoing)*6) / 1000000
    return {'currency': 'CNY', 'estimated': True, 'amount': float(total),
            'complete': unpriced == 0, 'unpriced_rows': unpriced, 'price_source': PRICE_SOURCE}


def prepare(store):
    with store.connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS operations_costs (run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, day TEXT NOT NULL, amount REAL NOT NULL, complete INTEGER NOT NULL)')


def record_cost(report, store=None):
    cost = estimate_cost(report.get('ai_usage') or [])
    store = store or active_store()
    if store is not None:
        prepare(store)
        moment = datetime.fromisoformat(report['started_at'])
        if moment.tzinfo is None:
            raise ValueError('cost timestamp requires timezone')
        started = moment.astimezone(timezone.utc).isoformat()
        day = moment.astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat()
        with store.connect() as db:
            db.execute('INSERT INTO operations_costs VALUES(?,?,?,?,?) ON CONFLICT(run_id) DO UPDATE SET amount=excluded.amount,complete=excluded.complete',
                       (report['run_id'], started, day, cost['amount'], int(cost['complete'])))
    return cost


def cost_totals(store, *, now=None):
    """Recorded project usage only; no provider balance checks or forecasts."""
    if store is None:
        return {'status': 'state_unavailable'}
    now = now or datetime.now(timezone.utc)
    prepare(store)
    day = now.astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat()
    with store.connect() as db:
        rows = db.execute('SELECT started_at,day,amount,complete FROM operations_costs').fetchall()
    return {'status': 'recorded_usage',
            'today_cny': round(sum(r[2] for r in rows if r[1] == day), 6),
            'month_cny': round(sum(r[2] for r in rows if r[1][:7] == day[:7]), 6),
            'recorded_since': min((r[0] for r in rows), default=None),
            'complete_pricing': all(r[3] for r in rows),
            'note': '仅为本项目已记录用量的费用估算，不是供应商账单或余额。'}


def finalize(path, workflow_status, *, publication_proof=None, published_state=None):
    if not path.exists():
        return 0
    raw = path.read_bytes()
    report = json.loads(raw)
    store = active_store()
    verified = False
    if publication_proof and publication_proof.is_file() and published_state and published_state.is_file():
        from .deployment_proof import valid_proof
        verified = valid_proof(json.loads(publication_proof.read_text()), raw, published_state.read_bytes())
    report["ai_cost"] = record_cost(report, store)
    report["operations"] = {
        "workflow_status": workflow_status,
        "cost_totals": cost_totals(store),
        "publication_verified": verified,
    }
    _atomic_write_text(path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if store:
        store.save_report(report)
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=Path("data/run-report.json"))
    parser.add_argument("--workflow-status", choices=("success", "failure", "cancelled"), default="success")
    parser.add_argument("--publication-proof", type=Path)
    parser.add_argument("--published-state", type=Path)
    args = parser.parse_args()
    return finalize(args.report, args.workflow_status, publication_proof=args.publication_proof,
                    published_state=args.published_state)


if __name__ == "__main__":
    raise SystemExit(main())
