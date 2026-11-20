"""Bounded cache/log maintenance. Default is a read-only deletion plan.

Never traverses business-state, release, backup or volume directories. Docker
owns image/cache GC; tagged images, containers and volumes are never removed.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import time

MIB = 1024 * 1024
DAY = 86400
RUNNER = Path('/opt/xiyunews-runner')
CI = Path('/opt/10eth-ci')
CODEQL = Path('/opt/hostedtoolcache/CodeQL')
VERSION = re.compile(r'(?:bin|externals)\.\d+\.\d+\.\d+')
SHA = re.compile(r'[0-9a-f]{40}')
LOG = re.compile(r'(?:Runner|Worker)_.*\.log')


def command(args):
    return subprocess.check_output(args, text=True, timeout=180).strip()


def size(path):
    if path.is_file():
        return path.stat().st_blocks * 512
    return int(command(['du', '-sx', '-B1', '--', str(path)]).split()[0])


def references(proc=Path('/proc')):
    """Only file/cwd/executable/mapping paths, never argv or environment."""
    result = set()
    for process in proc.iterdir():
        if not process.name.isdigit():
            continue
        try:
            links = [process/'cwd', process/'exe', *list((process/'fd').iterdir())]
            for link in links:
                try:
                    value = os.readlink(link).removesuffix(' (deleted)')
                except (FileNotFoundError, ProcessLookupError, OSError) as error:
                    if isinstance(error, PermissionError):
                        raise
                    continue
                if value.startswith('/'):
                    result.add(Path(value))
            for line in (process/'maps').read_text().splitlines():
                parts = line.split(maxsplit=5)
                if len(parts)==6 and parts[5].startswith('/'):
                    result.add(Path(parts[5].removesuffix(' (deleted)')))
        except (FileNotFoundError, ProcessLookupError):
            continue
        # Visibility failures are fatal: absence of evidence is not disuse.
    for line in (proc/'self/mountinfo').read_text().splitlines():
        result.add(Path(line.split()[4].replace(chr(92)+'040', ' ')))
    ids = command(['docker', 'ps', '-aq']).splitlines()
    if ids:
        mounts = command(['docker', 'inspect', '--format',
            '{{range .Mounts}}{{println .Source}}{{end}}', *ids])
        result.update(Path(p) for p in mounts.splitlines() if p.startswith('/'))
    return result


def in_use(path, refs):
    return any(p == path or path in p.parents for p in refs)


def safe_child(path, root):
    """Reject symlinks/aliased parents and broad roots, including a mount."""
    if path == root or not path.is_relative_to(root):
        return False
    try:
        return (root.resolve()==root and path.resolve()==path and
                not path.is_symlink() and not path.is_mount() and
                path.stat().st_dev==root.stat().st_dev)
    except FileNotFoundError:
        return False


def cap_candidates(rows, *, budget, max_age, now):
    """Evict oldest *eligible* entries; referenced entries consume the budget."""
    used = sum(row['bytes'] for row in rows)
    selected = []
    for row in sorted(rows, key=lambda x:x['mtime']):
        if row.get('protected'):
            continue
        if now-row['mtime']>max_age or used>budget:
            selected.append(row); used -= row['bytes']
    return selected


def plan(refs, *, runner=RUNNER, ci=CI, codeql=CODEQL, ci_locked=False, now=None):
    now = time.time() if now is None else now
    rows=[]
    def add(path, root, kind, min_age=0):
        if (not path.exists() or not safe_child(path,root) or
                now-path.stat().st_mtime<min_age):
            return
        info=path.stat()
        rows.append({'path':str(path),'root':str(root),'kind':kind,'bytes':size(path),
            'mtime':info.st_mtime,'identity':[info.st_dev,info.st_ino],
            'protected':in_use(path,refs) or (kind=='ci-cache' and now-info.st_mtime<DAY)})
    if runner.exists():
        current = {p.resolve() for p in (runner/'bin',runner/'externals') if p.is_symlink()}
        for path in runner.iterdir():
            if VERSION.fullmatch(path.name) and path not in current:
                add(path,runner,'old-runner',7*DAY)
        update=runner/'_work/_update'
        listener=update/'bin/Runner.Listener.dll'
        finished=runner/'update.finished'
        # A prepared future updater is NOT disposable. Require completed,
        # old staging and byte identity with an already installed version.
        if (listener.is_file() and finished.is_file() and
                now-finished.stat().st_mtime>DAY):
            value=hashlib.sha256(listener.read_bytes()).digest()
            installed=[p/'Runner.Listener.dll' for p in runner.glob('bin.*')
                       if VERSION.fullmatch(p.name) and not p.is_symlink()]
            if any(p.is_file() and hashlib.sha256(p.read_bytes()).digest()==value for p in installed):
                add(update,runner,'completed-update',7*DAY)
        for path in (runner/'_diag').glob('*.log'):
            if LOG.fullmatch(path.name):
                add(path,runner,'runner-log')
    if codeql.exists():
        for path in codeql.iterdir():
            if re.fullmatch(r'\d+\.\d+\.\d+',path.name):
                add(path,codeql,'retired-codeql',2*DAY)
    if ci.exists() and ci_locked:
        for work in (ci/'work').iterdir():
            if not SHA.fullmatch(work.name) or not safe_child(work,ci) or in_use(work,refs):
                continue
            for name in ('node_modules','.turbo'):
                add(work/name,ci,'ci-cache')
            for path in (work/'apps').glob('*/.next/cache'):
                add(path,ci,'ci-cache')
    chosen=[r for r in rows if r['kind'] not in ('runner-log','ci-cache') and not r['protected']]
    for kind,budget,age in [('runner-log',128*MIB,14*DAY),('ci-cache',512*MIB,7*DAY)]:
        chosen+=cap_candidates([r for r in rows if r['kind']==kind],budget=budget,max_age=age,now=now)
    return chosen


def remove(row, refs):
    path=Path(row['path']);root=Path(row['root'])
    if not safe_child(path,root) or in_use(path,refs):
        return False
    info=path.stat()
    if [info.st_dev,info.st_ino]!=row['identity']:
        raise RuntimeError('candidate changed since planning')
    if path.is_dir():
        if not shutil.rmtree.avoids_symlink_attacks:
            raise RuntimeError('safe directory deletion unavailable')
        shutil.rmtree(path)
    else:
        path.unlink()
    return True


@contextmanager
def ci_lock(path):
    try:fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    except FileNotFoundError:
        yield False;return
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):raise ValueError('unsafe CI lock')
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            yield False;return
        yield True
    finally:
        os.close(fd)


def main(apply=False):
    if os.geteuid()!=0:raise SystemExit('root required for complete process visibility')
    with ci_lock(CI/'run.lock') as locked:
        refs=references()
        rows=plan(refs,ci_locked=locked)
        print(json.dumps({'mode':'apply' if apply else 'dry-run','ci_locked':locked,
            'candidates':rows,'candidate_bytes':sum(r['bytes'] for r in rows)},sort_keys=True),flush=True)
        if not apply:return
        removed=[]
        # Recheck all process/mount references immediately before each batch.
        fresh=references()
        for row in rows:
            if remove(row,fresh):removed.append({'path':row['path'],'bytes':row['bytes']})
        # Built-in GC rechecks live Docker references and BuildKit leases.
        for args in (
            ['docker','image','prune','--force','--filter','until=168h'],
            ['docker','buildx','prune','--force','--max-used-space','512MB','--reserved-space','256MB'],
            ['journalctl','--rotate'],
            ['journalctl','--vacuum-size=256M','--vacuum-time=14days'],
        ):
            subprocess.run(args,check=True,timeout=240)
        print(json.dumps({'removed':removed,'removed_bytes':sum(r['bytes'] for r in removed),
                          'disk':shutil.disk_usage('/')._asdict()},sort_keys=True),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    # One operator/timer at a time; this lock does not stop production jobs.
    fd=os.open('/run/xiyunews-disk-maintenance.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    main(args.apply)
