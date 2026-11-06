from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Page:
    document_id: str
    source: str
    page: int
    text: str
    version: str = "unspecified"

    def __post_init__(self):
        if not self.document_id.strip() or not self.source.strip() or self.page < 1 or not self.text.strip():
            raise ValueError("Document ID, source, positive physical page and nonempty text required")


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    source: str
    page: int
    text: str
    start: int
    end: int
    version: str

    def payload(self):
        return asdict(self)


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float

    def as_dict(self):
        return {"score": self.score, **self.chunk.payload()}
