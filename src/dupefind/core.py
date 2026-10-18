"""Core duplicate-detection logic.

Strategy (fast to slow, so most files never get fully read):
  1. group by file size
  2. group by hash of the first 4 KiB
  3. group by full-content hash
"""
from __future__ import annotations

import hashlib
import os
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Iterator

CHUNK = 1024 * 1024
PARTIAL = 4096


def _hash_file(path: Path, limit: int | None = None) -> str:
    h = hashlib.blake2b(digest_size=16)
    remaining = limit
    with open(path, "rb") as f:
        while True:
            size = CHUNK if remaining is None else min(CHUNK, remaining)
            if size == 0:
                break
            buf = f.read(size)
            if not buf:
                break
            h.update(buf)
            if remaining is not None:
                remaining -= len(buf)
    return h.hexdigest()


def _walk(roots: Iterable[Path], min_size: int, exclude: set[str]) -> Iterator[Path]:
    for root in roots:
        if root.is_file():
            yield root
            continue
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            dirnames[:] = [d for d in dirnames if d not in exclude]
            for name in filenames:
                p = Path(dirpath) / name
                try:
                    if p.is_symlink() or not p.is_file():
                        continue
                    if p.stat().st_size >= min_size:
                        yield p
                except OSError:
                    continue


def find_duplicates(
    roots: Iterable[str | Path],
    min_size: int = 1,
    exclude: Iterable[str] = (".git", "node_modules", "__pycache__"),
) -> list[list[Path]]:
    """Return groups of identical files (each group has 2+ paths, oldest first)."""
    roots = [Path(r) for r in roots]
    excl = set(exclude)

    by_size: dict[int, list[Path]] = defaultdict(list)
    seen: set[tuple[int, int]] = set()  # (dev, inode) - skip hardlinks to same file
    for p in _walk(roots, min_size, excl):
        try:
            st = p.stat()
        except OSError:
            continue
        key = (st.st_dev, st.st_ino)
        if st.st_ino and key in seen:
            continue
        seen.add(key)
        by_size[st.st_size].append(p)

    def split(groups: Iterable[list[Path]], limit: int | None):
        for group in groups:
            if len(group) < 2:
                continue
            buckets: dict[str, list[Path]] = defaultdict(list)
            for p in group:
                try:
                    buckets[_hash_file(p, limit)].append(p)
                except OSError:
                    continue
            yield from (b for b in buckets.values() if len(b) > 1)

    partial = split(by_size.values(), PARTIAL)
    full = split(partial, None)

    result = [sorted(g, key=lambda p: (p.stat().st_mtime, str(p))) for g in full]
    result.sort(key=lambda g: g[0].stat().st_size * (len(g) - 1), reverse=True)
    return result


def human_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n} B"
