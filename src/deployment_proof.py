"""Validate private deployment evidence before a channel delivery can begin."""
from datetime import datetime,timezone
import hashlib
import re
from zoneinfo import ZoneInfo


def valid_proof(proof,report_bytes,state_bytes,*,now=None):
    now=now or datetime.now(timezone.utc)
    if proof.get('version')!=1 or proof.get('verified') is not True:return False
    if not str(proof.get('source_run_id') or '').isdecimal():return False
    if proof.get('source_report_sha256')!=hashlib.sha256(report_bytes).hexdigest():return False
    if proof.get('selection_sha256')!=hashlib.sha256(state_bytes).hexdigest():return False
    if proof.get('edition_date')!=now.astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat():return False
    for name in ('source_commit','artifact_commit'):
        if not re.fullmatch('[a-f0-9]{40}',str(proof.get(name,''))):return False
    try:
        verified=datetime.fromisoformat(proof['verified_at'].replace('Z','+00:00'))
        return verified.tzinfo is not None and -60 <= (now-verified).total_seconds() <= 86400
    except (ValueError,KeyError,TypeError):return False
