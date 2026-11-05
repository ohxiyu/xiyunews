"""Fetch large document blobs in bounded batches, then restore the full checkout."""
import base64
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time

MAX_CACHE_BYTES = 128 * 1024 * 1024


def blob_digest(body):
    return hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest()


def cache_root():
    value = os.environ.get('XIYUNEWS_DOCUMENT_CACHE', '')
    if not value:
        return None
    root = Path(value).absolute()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.resolve() != root or root.is_symlink() or root.stat().st_uid != os.getuid():
        raise ValueError('unsafe document cache')
    return root


def hydrate(*, batch_size=4, attempts=3):
    if not 1 <= batch_size <= 16:
        raise ValueError('invalid batch size')
    # Git checkout's single lazy fetch can lose a whole large image transfer.
    # Use ordinary Git object transfers, never rewrite files or the commit.
    raw = subprocess.check_output(['git', 'ls-tree', '-rz', 'HEAD', '--', 'project-docs'])
    objects = []
    for entry in raw.split(b'\0'):
        if not entry:
            continue
        mode, kind, digest = entry.split(b'\t', 1)[0].split()
        if kind != b'blob':
            continue
        value = digest.decode('ascii')
        if not re.fullmatch('[a-f0-9]{40}', value):
            raise ValueError('invalid Git object')
        objects.append(value)
    objects = sorted(set(objects))
    env = os.environ.copy()
    token = env.pop('GH_TOKEN', '')
    if token:
        # Read-only job token exists only in this process and its Git child.
        # No credentials in arguments, files, output, or later test steps.
        count = int(env.get('GIT_CONFIG_COUNT', '0'))
        encoded = base64.b64encode(('x-access-token:' + token).encode()).decode()
        for index, suffix in enumerate(('', '.git'), start=count):
            env[f'GIT_CONFIG_KEY_{index}'] = 'http.https://github.com/ohxiyu/xiyunews' + suffix + '.extraheader'
            env[f'GIT_CONFIG_VALUE_{index}'] = 'AUTHORIZATION: basic ' + encoded
        env['GIT_CONFIG_COUNT'] = str(count + 2)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'])
    cache = cache_root()
    needed = []
    for digest in objects:
        file = cache / digest if cache else None
        if file is None or not file.exists():
            needed.append(digest)
            continue
        info = file.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError('unsafe cached document blob')
        body = file.read_bytes()
        if blob_digest(body) != digest:
            raise ValueError('cached document blob digest mismatch')
        restored = subprocess.check_output(['git', 'hash-object', '-w', '--stdin'], input=body).decode().strip()
        if restored != digest:
            raise ValueError('restored Git object mismatch')
    used = sum(p.lstat().st_size for p in cache.iterdir()) if cache else 0
    for offset in range(0, len(needed), batch_size):
        batch = needed[offset:offset + batch_size]
        for attempt in range(attempts):
            try:
                subprocess.run(['git', 'fetch', '--quiet', '--no-tags', '--no-write-fetch-head',
                                '--no-recurse-submodules', '--filter=blob:none', 'origin', *batch],
                               env=env, check=True, capture_output=True, timeout=180)
                break
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                if attempt + 1 == attempts:
                    # Captured Git output can contain credential-bearing URLs.
                    raise RuntimeError('document blob batch download failed') from None
                time.sleep(2)
        for digest in batch:
            body = subprocess.check_output(['git', 'cat-file', 'blob', digest], env=env)
            if blob_digest(body) != digest:
                raise ValueError('downloaded document blob mismatch')
            if cache and used + len(body) <= MAX_CACHE_BYTES:
                fd, temporary = tempfile.mkstemp(prefix='.incoming-', dir=cache)
                try:
                    with os.fdopen(fd, 'wb') as stream:
                        stream.write(body)
                    try:
                        os.link(temporary, cache / digest)
                        used += len(body)
                    except FileExistsError:
                        pass
                finally:
                    os.unlink(temporary)
    subprocess.run(['git', 'sparse-checkout', 'disable'], env=env, check=True, capture_output=True, timeout=180)
    if subprocess.check_output(['git', 'rev-parse', 'HEAD']) != head:
        raise RuntimeError('checkout commit changed')
    print(f'Full checkout restored from the same commit; {len(objects)} verified blobs, {len(needed)} fetched.')


if __name__ == '__main__':
    hydrate()
