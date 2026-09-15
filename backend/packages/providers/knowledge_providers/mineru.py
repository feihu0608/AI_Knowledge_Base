from __future__ import annotations

from io import BytesIO
import time
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

import httpx

from .contracts import MinerUArtifact, ProviderMode


class MinerUParseError(RuntimeError):
    pass


class MinerUApiProvider:
    mode = ProviderMode.LIVE

    def __init__(self, *, base_url: str, api_key: str, timeout_seconds: float = 600,
                 poll_interval_seconds: float = 3, max_archive_bytes: int = 100 * 1024 * 1024,
                 api_transport: httpx.BaseTransport | None = None,
                 file_transport: httpx.BaseTransport | None = None) -> None:
        if not api_key:
            raise ValueError("MINERU_API_KEY is required in live mode")
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.max_archive_bytes = max_archive_bytes
        self._api = httpx.Client(
            base_url=base_url.rstrip("/"), timeout=60, transport=api_transport,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        # Presigned object-storage URLs must never receive the MinerU bearer token.
        self._files = httpx.Client(timeout=120, transport=file_transport)

    @staticmethod
    def _data(response: httpx.Response) -> dict:
        response.raise_for_status()
        body = response.json()
        if body.get("code") != 0 or not isinstance(body.get("data"), dict):
            raise MinerUParseError(f"MinerU API rejected request: {body.get('msg', 'unknown error')}")
        return body["data"]

    def parse(self, *, filename: str, content: bytes) -> MinerUArtifact:
        data_id = str(uuid4())
        slot = self._data(self._api.post("/file-urls/batch", json={
            "files": [{"name": filename, "data_id": data_id}], "model_version": "vlm",
            "enable_formula": True, "enable_table": True, "language": "ch",
        }))
        urls = slot.get("file_urls") or []
        batch_id = slot.get("batch_id")
        if not batch_id or len(urls) != 1:
            raise MinerUParseError("MinerU did not provide one upload URL")
        upload = self._files.put(urls[0], content=content, headers={"Content-Type": "application/octet-stream"})
        upload.raise_for_status()

        deadline = time.monotonic() + self.timeout_seconds
        result: dict | None = None
        while time.monotonic() < deadline:
            batch = self._data(self._api.get(f"/extract-results/batch/{batch_id}"))
            rows = batch.get("extract_result") or []
            result = next((row for row in rows if row.get("data_id") == data_id), rows[0] if rows else None)
            if result and result.get("state") == "done":
                break
            if result and result.get("state") in {"failed", "error"}:
                raise MinerUParseError(f"MinerU parse failed: {result.get('err_msg') or 'unknown error'}")
            time.sleep(self.poll_interval_seconds)
        else:
            raise MinerUParseError("MinerU parse timed out")

        archive_url = result.get("full_zip_url") if result else None
        if not archive_url:
            raise MinerUParseError("MinerU result is missing full_zip_url")
        archive = self._files.get(archive_url)
        archive.raise_for_status()
        if len(archive.content) > self.max_archive_bytes:
            raise MinerUParseError("MinerU result archive exceeds size limit")
        try:
            with ZipFile(BytesIO(archive.content)) as bundle:
                markdown_names = sorted(name for name in bundle.namelist() if name.lower().endswith(".md"))
                if not markdown_names:
                    raise MinerUParseError("MinerU archive contains no Markdown output")
                info = bundle.getinfo(markdown_names[0])
                if info.file_size > self.max_archive_bytes:
                    raise MinerUParseError("MinerU Markdown output exceeds size limit")
                markdown = bundle.read(info).decode("utf-8").strip()
        except BadZipFile as exc:
            raise MinerUParseError("MinerU returned an invalid ZIP archive") from exc
        if not markdown:
            raise MinerUParseError("MinerU returned empty Markdown")
        page_markers = markdown.count("<!-- page")
        return MinerUArtifact(markdown=markdown, page_count=max(1, page_markers), warnings=[])
