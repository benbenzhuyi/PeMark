#!/usr/bin/env python3
"""One-command V8.5.4 release verification for a fresh Windows machine.

Run this from the repository root in an interactive desktop session:

    python tools/verify_release_v8_5_4.py

It rebuilds the release generator twice, compares the binaries, inspects the PE
structure, and then runs the machine-code, section/ASLR, Open/encoding and GUI
suites. The last block of output is a JSON summary - paste that back as-is.
"""
import ctypes as c
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "src/current/generate_markdown_editor_v8_5_4.py"
BINARY = ROOT / "bin/current/pemark_x64_v8_5_4.exe"
TOOLS = ROOT / "tools"
EXPECTED_EXE_SHA256 = "aa8de9cda9ed90a2cf66a3a93e021dc91cc192073078a90c53fa9669f478c5cc"
EXPECTED_SECTIONS = ["\\.text", "\\.rdata", "\\.idata", "\\.bss", "\\.reloc", "\\.pdata"]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(label, args, cwd=None, timeout=900, env=None):
    started = time.perf_counter()
    proc = subprocess.run([sys.executable] + args, cwd=str(cwd or ROOT),
                          capture_output=True, text=True, timeout=timeout,
                          env=env)
    return {
        "step": label,
        "status": "PASS" if proc.returncode == 0 else "FAIL",
        "exit_code": proc.returncode,
        "seconds": round(time.perf_counter() - started, 1),
        "tail": (proc.stdout or "").strip().splitlines()[-3:],
        "stderr_tail": (proc.stderr or "").strip().splitlines()[-3:],
    }


def main():
    results, notes = [], []
    started = time.time()
    environment = {
        "windows": platform.platform(),
        "python": sys.version.split()[0],
        "machine": platform.machine(),
        "session_interactive": bool(c.windll.user32.GetForegroundWindow()),
    }

    try:
        import unicorn  # noqa: F401
        results.append({"step": "import unicorn", "status": "PASS", "exit_code": 0,
                        "seconds": 0.0, "tail": [unicorn.__version__], "stderr_tail": []})
    except Exception as exc:
        results.append({"step": "import unicorn", "status": "FAIL", "exit_code": 1,
                        "seconds": 0.0, "tail": [],
                        "stderr_tail": ["pip install -r requirements-dev.txt: %r" % exc]})
        notes.append("Install the test dependency before rerunning.")

    if not GENERATOR.exists():
        notes.append("generator missing: %s (check out the release branch)"
                     % GENERATOR.relative_to(ROOT))
    else:
        hashes = []
        for attempt in (1, 2):
            step = run("deterministic build %d" % attempt, [str(GENERATOR)])
            hashes.append(sha256(BINARY) if BINARY.exists() else None)
            results.append(step)
        if hashes[0] and hashes[0] == hashes[1]:
            results.append({"step": "deterministic binary", "status": "PASS",
                            "exit_code": 0, "seconds": 0.0,
                            "tail": [hashes[0]], "stderr_tail": []})
        else:
            results.append({"step": "deterministic binary", "status": "FAIL",
                            "exit_code": 1, "seconds": 0.0,
                            "tail": [str(h) for h in hashes], "stderr_tail": []})

        if EXPECTED_EXE_SHA256 != "PENDING":
            ok = hashes[0] == EXPECTED_EXE_SHA256
            results.append({"step": "release hash matches manifest",
                            "status": "PASS" if ok else "FAIL",
                            "exit_code": 0 if ok else 1, "seconds": 0.0,
                            "tail": [hashes[0] or "missing"], "stderr_tail": []})

        results.append(run("inspect PE", ["tools/inspect_pe.py",
                                          "bin/current/pemark_x64_v8_5_4.exe"]))
        results.append(run("machine-code regressions",
                           ["tools/test_v8_5_1.py",
                            "src/current/generate_markdown_editor_v8_5_4.py"]))
        # The suites default to the development channel; point them at the
        # release channel so what is verified is the shipped artifact.
        release_env = dict(os.environ)
        release_env["PEMARK_GENERATOR"] = str(GENERATOR)
        release_env["PEMARK_EXE"] = str(BINARY)
        results.append(run("section separation, ASLR and page protections",
                           ["tools/test_v8_5_4_sections.py"], env=release_env))
        results.append(run("unwind metadata structure",
                           ["tools/test_v8_5_4_unwind.py"], env=release_env))
        results.append(run("Open / encoding transaction matrix",
                           ["tools/test_v8_5_2_open_encoding.py"], env=release_env))
        results.append(run("GUI smoke suite",
                           ["tools/smoke_test_v8_5_1.py",
                            "bin/current/pemark_x64_v8_5_4.exe"]))

    failed = [r["step"] for r in results if r["status"] == "FAIL"]
    summary = {
        "schema": 1,
        "release": "V8.5.4",
        "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_seconds": round(time.time() - started, 1),
        "environment": environment,
        "binary": {
            "path": str(BINARY.relative_to(ROOT)),
            "size": BINARY.stat().st_size if BINARY.exists() else None,
            "sha256": sha256(BINARY) if BINARY.exists() else None,
            "expected_sha256": EXPECTED_EXE_SHA256,
        },
        "steps": results,
        "failed_steps": failed,
        "notes": notes,
        "status": "PASS" if results and not failed else "FAIL",
    }
    print("=" * 72)
    print("Paste the JSON block below back to the maintainer.")
    print("=" * 72)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
