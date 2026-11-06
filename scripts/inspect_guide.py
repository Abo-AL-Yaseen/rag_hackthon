"""Extract and render the complete supplied guide without modifying it."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import fitz


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    source = root / "IEEE_RAG_Hackathon_Judging_Guide_AR.pdf"
    output = root / "tmp" / "pdfs"
    output.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    expected = "aa74d0f5e2b9f82695063f02f945db7bec5aaa1dae9f526d0b1d4b3fa360f4cc"
    if digest != expected:
        raise ValueError("Guide changed: review the rubric before updating the expected hash.")
    with fitz.open(source) as document:
        if len(document) != 12:
            raise ValueError(f"Expected 12 pages, found {len(document)}")
        pages = []
        for number, page in enumerate(document, start=1):
            text = page.get_text(sort=True)
            if not text.strip():
                raise ValueError(f"Page {number} has no extractable text; inspect/OCR it.")
            stem = output / f"page-{number:02d}"
            stem.with_suffix(".txt").write_text(text, encoding="utf-8")
            page.get_pixmap(matrix=fitz.Matrix(1.3, 1.3)).save(str(stem.with_suffix(".png")))
            pages.append({"page": number, "characters": len(text)})
    report = {"source": source.name, "sha256": digest, "pages": pages}
    (output / "guide_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Verified {len(pages)} pages; text and PNGs saved to {output}")


if __name__ == "__main__":
    main()
