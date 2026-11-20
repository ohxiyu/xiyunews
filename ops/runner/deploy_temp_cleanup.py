"""Reclaim only verified, unused actions-gh-pages clones in the runner home."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import stat
import time

ROOT = Path('/home/xiyunews-runner')
NAME = re.compile(r'actions_github_pages_([0-9]{13})')


def process_references(root: Path, proc: Path = Path('/proc')) -> set[str]:
    """Never read process arguments or environment; inspect cwd/fd links only."""
    references = set()
    for process in proc.iterdir():
        if not process.name.isdigit():
            continue
        own = True  # An unreadable uid cannot be assumed to be another account.
        try:
            own = process.stat().st_uid == os.getuid()
            links = [process / 'cwd', *list((process / 'fd').iterdir())]
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError:
            if own:
                raise RuntimeError('cannot inspect an owned process')
            continue
        for link in links:
            try:
                target = Path(os.readlink(link))
            except (FileNotFoundError, ProcessLookupError):
                continue
            except PermissionError:
                if own:
                    raise RuntimeError('cannot inspect an owned process link')
                continue
            except OSError:
                continue
            if root in target.parents:
                references.add(target.relative_to(root).parts[0])
    return references


def cleanup(root: Path = ROOT, *, min_age: float = 86400, apply: bool = False,
            now: float | None = None, proc: Path = Path('/proc')) -> dict:
    root = root.absolute()
    if root.is_symlink() or root.resolve() != root or root.stat().st_uid != os.getuid():
        raise ValueError('unsafe runner home')
    if min_age < 0:
        raise ValueError('invalid minimum age')
    fd = os.open(root / '.deployment-temp-cleanup.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            raise ValueError('unsafe cleanup lock')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'removed': 0, 'eligible': 0, 'in_use': 0, 'skipped': 'locked'}
        return _cleanup_verified(root, min_age=min_age, apply=apply, now=now, proc=proc)
    finally:
        os.close(fd)


def _cleanup_verified(root: Path, *, min_age: float, apply: bool,
                      now: float | None, proc: Path) -> dict:
    now = time.time() if now is None else now
    try:
        references = process_references(root, proc)
    except RuntimeError:
        return {'removed': 0, 'eligible': 0, 'in_use': 0, 'skipped': 'process_visibility'}
    result = {'removed': 0, 'eligible': 0, 'in_use': 0}
    device = root.stat().st_dev
    for path in sorted(root.iterdir()):
        match = NAME.fullmatch(path.name)
        if not match or int(match[1]) / 1000 > now - min_age:
            continue
        info = path.lstat()
        git = path / '.git'
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
                or info.st_dev != device or path.is_mount()
                or git.is_symlink() or not git.is_dir()):
            continue
        if path.name in references:
            result['in_use'] += 1
            continue
        result['eligible'] += 1
        if apply:
            fresh = path.lstat()
            if (fresh.st_dev, fresh.st_ino) != (info.st_dev, info.st_ino):
                raise ValueError('deployment clone changed during cleanup')
            # Linux rmtree uses directory fds and does not traverse symlinks.
            shutil.rmtree(path)
            result['removed'] += 1
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--min-age-hours', type=float, default=24)
    args = parser.parse_args()
    if args.apply and args.dry_run:
        parser.error('choose apply or dry-run')
    print(json.dumps({'event': 'deployment_temp_cleanup', **cleanup(
        min_age=args.min_age_hours * 3600, apply=args.apply)}))
