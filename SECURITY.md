# Security policy

English | [简体中文](SECURITY.zh-CN.md)

## Supported version

Security fixes currently target the latest V8.5.x Preview source and binary.
Historical binaries under `archive/` are retained for research and are not
supported.

## Reporting a vulnerability

Do not include sensitive documents, exploit material or private machine data in
a public issue. Before publication, configure GitHub private vulnerability
reporting under **Settings → Security → Private vulnerability reporting** and
use that channel for security reports.

Include the affected version and SHA-256, Windows version, reproducible steps,
expected and observed behavior, and whether the issue can corrupt or disclose a
document. Acknowledgement and remediation times are best-effort while the
project remains a preview.

## Binary verification

The V8.5.1 Preview executable is unsigned. Its expected SHA-256 is:

```text
b8b07fe43a20cb21e7e33d58a6300f4f2d388dcbc9a26e0306bdaa231f73a39f
```
