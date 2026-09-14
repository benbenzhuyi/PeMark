#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys

root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
excluded_dirs={'.git','__pycache__','.pytest_cache','.mypy_cache','.venv','local-reference'}
excluded_files={'SHA256SUMS.txt','Thumbs.db','Desktop.ini'}

for p in sorted(x for x in root.rglob('*') if x.is_file()):
    rel=p.relative_to(root)
    if rel.parts[:2] == ('bin', 'test'):
        continue
    if any(part in excluded_dirs for part in rel.parts):
        continue
    if rel.name in excluded_files or rel.suffix.lower() in {'.pyc','.pyo','.log','.dmp'}:
        continue
    h=hashlib.sha256(p.read_bytes()).hexdigest()
    print(h, rel.as_posix())
