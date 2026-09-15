from __future__ import annotations

from pathlib import Path

from .contracts import MinerUArtifact, MinerUProvider, ProviderMode


class PlainTextDocumentParser:
    """Parse text formats that MinerU does not accept without losing headings."""

    mode = ProviderMode.LIVE

    def parse(self, *, filename: str, content: bytes) -> MinerUArtifact:
        for encoding in ("utf-8-sig", "gb18030"):
            try:
                markdown = content.decode(encoding).strip()
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError("text_document_encoding_unsupported")
        if not markdown:
            raise ValueError("empty_document")
        return MinerUArtifact(
            markdown=markdown,
            page_count=1,
            warnings=["native_text_parser_used"],
        )


class RoutingDocumentParser:
    """Route native text to a deterministic parser and rich documents to MinerU."""

    mode = ProviderMode.LIVE

    def __init__(self, *, mineru: MinerUProvider, text_parser: MinerUProvider | None = None) -> None:
        self._mineru = mineru
        self._text_parser = text_parser or PlainTextDocumentParser()

    def parse(self, *, filename: str, content: bytes) -> MinerUArtifact:
        if Path(filename).suffix.lower() in {".md", ".txt"}:
            return self._text_parser.parse(filename=filename, content=content)
        return self._mineru.parse(filename=filename, content=content)
