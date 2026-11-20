import importlib.util
import os
from pathlib import Path
import pytest

pytest.importorskip('fcntl')

SPEC=importlib.util.spec_from_file_location('disk_maintenance',Path(__file__).parents[1]/'ops/maintenance/disk_maintenance.py')
m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m)
NOW=2_000_000_000


def directory(path,age=20):
    path.mkdir(parents=True,exist_ok=True)
    (path/'file').write_bytes(b'test')
    os.utime(path,(NOW-age*m.DAY,NOW-age*m.DAY))
    return path


def test_plan_preserves_current_versions_references_releases_and_business_data(tmp_path):
    runner=tmp_path/'runner';runner.mkdir()
    current=directory(runner/'bin.2.3.4');(runner/'bin').symlink_to(current)
    external=directory(runner/'externals.2.3.4');(runner/'externals').symlink_to(external)
    old=directory(runner/'bin.2.3.3')
    held=directory(runner/'externals.2.3.3')
    directory(runner/'state');directory(runner/'backups')
    ci=tmp_path/'ci';work=ci/'work'/('a'*40)
    cache=directory(work/'node_modules');release=directory(work/'server-artifact')
    codeql=directory(tmp_path/'codeql'/'2.27.4')
    refs={held/'file',cache/'file'}
    rows=m.plan(refs,runner=runner,ci=ci,codeql=codeql.parent,ci_locked=True,now=NOW)
    assert {r['path'] for r in rows}=={str(old),str(codeql)}
    assert all(r['kind']!='ci-cache' for r in rows)
    assert release.exists() and current.exists()


def test_ci_lock_and_recent_cache_are_preserved_while_cold_cache_is_capped(tmp_path,monkeypatch):
    ci=tmp_path/'ci';old=directory(ci/'work'/('a'*40)/'node_modules')
    recent=directory(ci/'work'/('b'*40)/'node_modules',age=0)
    monkeypatch.setattr(m,'size',lambda p:600*m.MIB)
    kwargs=dict(runner=tmp_path/'absent',ci=ci,codeql=tmp_path/'missing',now=NOW)
    assert not m.plan(set(),ci_locked=False,**kwargs)
    rows=m.plan(set(),ci_locked=True,**kwargs)
    assert [r['path'] for r in rows]==[str(old)]
    assert str(recent) not in [r['path'] for r in rows]


def test_symlink_escape_and_aliased_parent_are_never_candidates(tmp_path):
    ci=tmp_path/'ci';(ci/'work').mkdir(parents=True)
    other=directory(tmp_path/'protected')
    (ci/'work'/('a'*40)).symlink_to(other,target_is_directory=True)
    assert not m.safe_child(ci/'work'/('a'*40)/'file',ci)
    assert not m.plan(set(),runner=tmp_path/'no',ci=ci,codeql=tmp_path/'no2',ci_locked=True,now=NOW)
    assert not m.safe_child(ci,ci)


def test_remove_rechecks_live_references_and_inode(tmp_path):
    root=tmp_path/'root';path=directory(root/'cache')
    s=path.stat();row={'path':str(path),'root':str(root),'identity':[s.st_dev,s.st_ino],'kind':'ci-cache'}
    assert not m.remove(row,{path/'file'})
    assert path.exists()
    row['identity']=[s.st_dev,s.st_ino+1]
    with pytest.raises(RuntimeError,match='changed'):m.remove(row,set())
    row['identity']=[s.st_dev,s.st_ino]
    assert m.remove(row,set())
    assert not path.exists()


def test_completed_update_requires_matching_installed_payload(tmp_path):
    runner=tmp_path/'runner';current=directory(runner/'bin.2.3.4')
    (current/'Runner.Listener.dll').write_bytes(b'installed')
    (runner/'bin').symlink_to(current)
    update=directory(runner/'_work/_update')
    (update/'bin').mkdir();listener=update/'bin/Runner.Listener.dll';listener.write_bytes(b'future')
    finished=runner/'update.finished';finished.touch();os.utime(finished,(NOW-10*m.DAY,)*2)
    os.utime(update,(NOW-10*m.DAY,)*2)
    kwargs=dict(runner=runner,ci=tmp_path/'no',codeql=tmp_path/'no2',now=NOW)
    assert not m.plan(set(),**kwargs)
    listener.write_bytes(b'installed')
    assert [r['path'] for r in m.plan(set(),**kwargs)]==[str(update)]
    assert not m.plan({listener},**kwargs)


def test_retention_keeps_protected_data_even_over_budget():
    rows=[{'mtime':1,'bytes':300,'protected':True},
          {'mtime':2,'bytes':200,'protected':False},
          {'mtime':3,'bytes':100,'protected':False}]
    assert m.cap_candidates(rows,budget=256,max_age=100,now=10)==rows[1:]


def test_ci_lock_does_not_interrupt_an_active_builder_or_follow_a_symlink(tmp_path):
    import fcntl
    lock=tmp_path/'run.lock';lock.touch()
    with lock.open() as owner:
        fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with m.ci_lock(lock) as acquired:assert not acquired
    with m.ci_lock(lock) as acquired:assert acquired
    alias=tmp_path/'alias';alias.symlink_to(lock)
    with pytest.raises(OSError):
        with m.ci_lock(alias):pass
