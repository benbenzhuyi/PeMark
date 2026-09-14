# V8.5.2 safety fixtures

Run `python tools/generate_v8_5_2_fixtures.py` to reproduce `fixtures/`.

The corpus covers empty UTF-8, LF/CRLF, UTF-8 BOM, UTF-16LE BOM, malformed
UTF-8, embedded NUL and a small allocation-boundary seed. Larger capacity files
remain generated tests so the repository does not duplicate large artifacts.

`SHA256SUMS` is part of the fixture contract. Update it only when a reviewed
contract change intentionally changes the corpus.

