"""Citation construction/validation, not a claim-support or faithfulness judge."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Citation:
    chunk_id: str
    document_id: str
    source: str
    page: int
    quote: str

    @property
    def label(self):
        return f"[{self.source}, p. {self.page}]"


def cite(hit, quote=None):
    c = hit.chunk
    quote = c.text if quote is None else quote
    if not quote.strip() or quote not in c.text:
        raise ValueError("Citation quote must be an exact nonempty substring of retrieved text")
    return Citation(c.chunk_id, c.document_id, c.source, c.page, quote)


def validate_citation(citation, hits):
    return any(citation.chunk_id == h.chunk.chunk_id and citation.document_id == h.chunk.document_id
               and citation.source == h.chunk.source and citation.page == h.chunk.page
               and bool(citation.quote.strip()) and citation.quote in h.chunk.text for h in hits)
