#!/usr/bin/env python3
"""Build V8.6.3 twice and require a deterministic release binary."""
from pathlib import Path
import hashlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "src/current/generate_markdown_editor_v8_6_3.py"
BINARY = ROOT / "bin/current/pemark_x64_v8_6_3.exe"
EXPECTED = "5fe17a495f691747e33d3372a78f202b442ae67cf55af2414ecba4a769186b21"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


hashes = []
for build_number in (1, 2):
    subprocess.run([sys.executable, str(GENERATOR)], cwd=ROOT, check=True)
    digest = sha256(BINARY)
    hashes.append(digest)
    print(f"build {build_number}: {digest}")

if hashes[0] != hashes[1]:
    raise SystemExit("non-deterministic build: consecutive hashes differ")
if hashes[0] != EXPECTED:
    raise SystemExit(f"release hash mismatch: expected {EXPECTED}")

print(f"MATCH: {BINARY.relative_to(ROOT)}")
