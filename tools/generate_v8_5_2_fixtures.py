#!/usr/bin/env python3
"""Generate deterministic V8.5.2 file-safety fixtures."""
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "v8_5_2" / "fixtures"

FILES = {
    "empty_utf8.md": b"",
    "utf8_lf.md": "# UTF-8\n中文 English 日本語 한국어\nemoji: 😀🚀\n".encode(),
    "utf8_crlf.md": "# CRLF\r\nline two\r\n中文 😀\r\n".encode(),
    "utf8_bom.md": b"\xef\xbb\xbf" + "# BOM\n中文 😀\n".encode(),
    "utf16le_bom.md": b"\xff\xfe" + "# UTF-16LE\r\n中文 😀\r\n".encode("utf-16le"),
    "malformed_utf8.md": b"# invalid\n\xf0\x28\x8c\x28\n",
    "embedded_nul_utf8.md": b"before\x00after\n",
    "boundary_text_utf8.md": ("# boundary\n" + "a" * 4093 + "\n").encode(),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in FILES.items():
        (OUT / name).write_bytes(data)
    lines = [f"{sha256(data).hexdigest()}  {name}" for name, data in sorted(FILES.items())]
    (OUT / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")
    print(f"generated {len(FILES)} fixtures in {OUT}")


if __name__ == "__main__":
    main()

