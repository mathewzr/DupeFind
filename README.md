# dupefind

Find duplicate files by content, see how much space they waste, and optionally clean them up. Pure Python, **zero dependencies**.

## Install

```bash
pip install .          # or: pip install git+https://github.com/YOUR-USERNAME/dupefind
```

## Usage

```bash
dupefind ~/Downloads ~/Pictures        # report duplicates
dupefind . --min-size 1M               # ignore files under 1 MB
dupefind . -x build -x .cache          # skip extra folders
dupefind . --json > report.json        # machine-readable
dupefind . --delete                    # delete extras (asks first)
```

Example output:

```
12.4 MB x 3
  keep  /home/me/Pictures/trip.zip
  dup   /home/me/Downloads/trip.zip
  dup   /home/me/Downloads/trip (1).zip

1 duplicate group(s), 24.8 MB reclaimable.
```

The **oldest** file in each group is kept; the rest are marked `dup`.

## How it works

Files are compared in three passes, cheapest first, so most files are never fully read:

1. Group by file size
2. Group by hash of the first 4 KiB
3. Group by full BLAKE2b hash

Symlinks are ignored, and hardlinks to the same file are not counted as duplicates.

## Development

```bash
pip install -e . pytest
pytest
```

## License

MIT
