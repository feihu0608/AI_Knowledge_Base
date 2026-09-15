from __future__ import annotations

from pathlib import Path
import re


class LocalObjectStorage:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    @staticmethod
    def safe_filename(filename: str) -> str:
        leaf = Path(filename).name
        safe = re.sub(r"[^\w.()\-\u4e00-\u9fff]+", "_", leaf, flags=re.UNICODE).strip("._")
        return safe[:180] or "document.bin"

    def put_source(self, *, tenant_id: str, document_id: str, version_id: str,
                   filename: str, content: bytes) -> str:
        relative = Path(tenant_id) / "documents" / document_id / version_id / self.safe_filename(filename)
        target = (self.root / relative).resolve()
        if self.root not in target.parents:
            raise ValueError("invalid storage path")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".upload")
        temporary.write_bytes(content)
        temporary.replace(target)
        return relative.as_posix()

    def delete(self, object_key: str) -> None:
        target = (self.root / object_key).resolve()
        if self.root in target.parents:
            target.unlink(missing_ok=True)

    def read(self, object_key: str) -> bytes:
        target = (self.root / object_key).resolve()
        if self.root not in target.parents:
            raise ValueError("invalid storage path")
        return target.read_bytes()
