import os
import time

from dupefind import find_duplicates, human_size
from dupefind.cli import main, parse_size


def make(tmp_path, name, data, mtime=None):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    if mtime:
        os.utime(p, (mtime, mtime))
    return p


def test_finds_duplicates_oldest_first(tmp_path):
    now = time.time()
    new = make(tmp_path, "b.txt", b"hello world", now)
    old = make(tmp_path, "sub/a.txt", b"hello world", now - 100)
    make(tmp_path, "c.txt", b"different!!")
    groups = find_duplicates([tmp_path])
    assert len(groups) == 1
    assert groups[0] == [old, new]


def test_same_size_different_content_not_duplicate(tmp_path):
    make(tmp_path, "a", b"x" * 10000)
    make(tmp_path, "b", b"x" * 9999 + b"y")
    assert find_duplicates([tmp_path]) == []


def test_min_size_and_exclude(tmp_path):
    make(tmp_path, "a", b"tiny")
    make(tmp_path, "b", b"tiny")
    make(tmp_path, "node_modules/c", b"tiny")
    assert len(find_duplicates([tmp_path], min_size=1)[0]) == 2
    assert find_duplicates([tmp_path], min_size=100) == []


def test_hardlinks_not_counted(tmp_path):
    a = make(tmp_path, "a", b"data")
    os.link(a, tmp_path / "link")
    assert find_duplicates([tmp_path]) == []


def test_cli_delete(tmp_path):
    make(tmp_path, "a", b"same", time.time() - 50)
    dup = make(tmp_path, "b", b"same")
    assert main([str(tmp_path), "--delete", "-y"]) == 0
    assert not dup.exists()
    assert (tmp_path / "a").exists()


def test_helpers():
    assert human_size(2048) == "2.0 KB"
    assert parse_size("5M") == 5 * 1024**2
    assert parse_size("10k") == 10240
