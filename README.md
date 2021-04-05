# filecleaner
A script for finding unused files

```
usage: filecleaner.py [-h] [--root ROOT] [--days N] [--pkg-days N] [--size BYTES] [--ignore [PATH ...]]
                      [--ignore-file FILE] [--package-manager PM] [--cache FILE]

Find unused files

optional arguments:
  -h, --help            show this help message and exit
  --root ROOT           the root directory to scan
  --days N              filter directories older than N days
  --pkg-days N          filter packages older than N days
  --size BYTES          filter directories larger than BYTES
  --ignore [PATH ...]   Ignore files under PATH
  --ignore-file FILE    Ignore files listed in FILE
  --package-manager PM  Used for finding which package owns a file
  --cache FILE          Load/save state to a file
```