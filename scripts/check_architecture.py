from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "architecture-baseline.json"


def main() -> int:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    errors: list[str] = []
    document = ROOT / baseline["architecture_document"]
    actual = hashlib.sha256(document.read_bytes()).hexdigest().upper()
    if actual != baseline["sha256"]:
        errors.append(f"architecture hash mismatch: expected {baseline['sha256']}, got {actual}")
    for path in baseline["required_directories"]:
        if not (ROOT / path).is_dir():
            errors.append(f"required module directory missing: {path}")
    for path, tokens in baseline["required_evidence"].items():
        target = ROOT / path
        if not target.is_file():
            errors.append(f"required evidence missing: {path}")
            continue
        text = target.read_text(encoding="utf-8")
        for token in tokens:
            if token not in text:
                errors.append(f"required token missing: {path} -> {token}")
    for path, max_lines in baseline["thin_entrypoints"].items():
        target = ROOT / path
        if not target.is_file():
            errors.append(f"entrypoint missing: {path}")
        elif len(target.read_text(encoding="utf-8").splitlines()) > max_lines:
            errors.append(f"entrypoint too large: {path}")
    for error in errors:
        print(f"ARCHITECTURE_GUARD_FAIL: {error}")
    if errors:
        return 1
    print(f"ARCHITECTURE_GUARD_PASS: {baseline['version']} sha256={actual}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

