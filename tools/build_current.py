#!/usr/bin/env python3
"""Build V8.5.1 twice and require a deterministic release binary."""
from pathlib import Path
import hashlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "src/current/generate_markdown_editor_v8_5_1.py"
BINARY = ROOT / "bin/current/pemark_x64_v8_5_1.exe"
EXPECTED = "b8b07fe43a20cb21e7e33d58a6300f4f2d388dcbc9a26e0306bdaa231f73a39f"


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
