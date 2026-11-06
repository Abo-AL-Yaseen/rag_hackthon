"""Page-preserving PDF/JSON ingestion and token-budgeted stable chunks."""
import hashlib
import json
from pathlib import Path
import uuid

import fitz

from .schema import Chunk, Page


def load_pages(path: Path) -> list[Page]:
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        pages = []
        with fitz.open(path) as doc:
            for number, page in enumerate(doc, 1):
                # Sort text blocks, preserving their logical character/word order.
                # Text-level sort=True reorders RTL words by screen coordinates.
                blocks=page.get_text('blocks',sort=True)
                text='\n'.join(block[4].strip() for block in blocks if block[6]==0).strip()
                if not text:
                    raise ValueError(f"No extractable text on {path.name} page {number}; OCR required")
                pages.append(Page(path.stem, path.name, number, text, "unspecified"))
    elif path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        pages = [Page(**{"version": data.get("version", "unspecified"), **record}) for record in data["pages"]]
    else:
        raise ValueError("Supported ingestion formats are PDF and page-structured JSON")
    if not pages:
        raise ValueError("Document contains no pages")
    identities = [(p.document_id, p.page) for p in pages]
    if len(identities) != len(set(identities)):
        raise ValueError("Duplicate document/page identity")
    return pages


def chunk_pages(pages: list[Page], tokenizer, max_tokens=240, overlap=32) -> list[Chunk]:
    if max_tokens < 1 or overlap < 0 or overlap >= max_tokens:
        raise ValueError("Require 0 <= overlap < max_tokens")
    # Include E5 passage prefix and special tokens in the 512-token model budget.
    overhead = len(tokenizer("passage: ", add_special_tokens=True)["input_ids"])
    if max_tokens + overhead > 512:
        raise ValueError("Chunk budget exceeds E5 token limit with prefix/special tokens")
    chunks = []
    for page in pages:
        encoded = tokenizer(page.text, add_special_tokens=False, return_offsets_mapping=True, truncation=False)
        offsets = encoded["offset_mapping"]
        if not offsets:
            raise ValueError("Page produced no tokens")
        for start_token in range(0, len(offsets), max_tokens - overlap):
            window = offsets[start_token:start_token + max_tokens]
            start, end = window[0][0], window[-1][1]
            text = page.text[start:end]
            # Retokenization at substring boundaries can differ; verify actual prefixed input.
            if len(tokenizer("passage: " + text, add_special_tokens=True)["input_ids"]) > 512:
                raise ValueError("Retokenized chunk exceeds model limit")
            content_hash = hashlib.sha256(text.encode()).hexdigest()
            identity = f"{page.document_id}:{page.version}:{page.page}:{start}:{end}:{content_hash}"
            chunks.append(Chunk(str(uuid.uuid5(uuid.NAMESPACE_URL, identity)), page.document_id,
                                page.source, page.page, text, start, end, page.version))
            if start_token + max_tokens >= len(offsets):
                break
    return chunks


def corpus_hash(chunks):
    return hashlib.sha256(json.dumps([c.payload() for c in chunks], ensure_ascii=False,
                                     sort_keys=True).encode()).hexdigest()
