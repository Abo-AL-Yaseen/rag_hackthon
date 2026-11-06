"""Server-owned exact excerpts: a provider selects IDs, never authors answer text."""
from dataclasses import dataclass
import hashlib
import re
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .contracts import StrictModel, Reason, GenerationDraft


class SelectionDraft(StrictModel):
    status: Literal['answered', 'insufficient_evidence']
    reason: Reason
    selection_ids: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(max_length=4)

    @model_validator(mode='after')
    def consistent_selection(self):
        if len(set(self.selection_ids)) != len(self.selection_ids):
            raise ValueError('Duplicate selections')
        if self.status=='answered' and (not self.selection_ids or self.reason!='supported'):
            raise ValueError('Answered selection requires evidence')
        if self.status=='insufficient_evidence' and (self.selection_ids or self.reason=='supported'):
            raise ValueError('Refusal cannot select evidence')
        return self


@dataclass(frozen=True)
class ExactSpan:
    selection_id: str
    chunk_id: str
    start: int
    end: int
    excerpt: str


def candidate_spans(hits):
    """Bounded sentence candidates; decimals retain their internal punctuation.

    Offsets are chunk-relative Python character offsets. No text normalization,
    translation, number conversion or semantic inference is performed.
    """
    result={}
    for hit in hits:
        text=hit.chunk.text
        begin=0
        ends=[match.end() for match in re.finditer(r'[.!?؟](?=\s|$)|\n',text)]
        if not ends or ends[-1]!=len(text):
            ends.append(len(text))
        for end in ends:
            piece=text[begin:end]
            left=begin+len(piece)-len(piece.lstrip())
            right=end-(len(piece)-len(piece.rstrip()))
            begin=end
            quote=text[left:right]
            if not quote or len(quote)>1500:
                continue
            digest=hashlib.sha256((hit.chunk.chunk_id+'\0'+str(left)+':'+str(right)+'\0'+quote).encode('utf-8')).hexdigest()
            ident='X'+digest[:32]
            result[ident]=ExactSpan(ident,hit.chunk.chunk_id,left,right,quote)
            if len(result)>=128:
                return result
    return result


def expand_selection(draft, hits):
    """Resolve only candidates from this request; caller maps missing IDs to an error."""
    spans=candidate_spans(hits)
    claims=[]
    for ident in draft.selection_ids:
        span=spans[ident]
        claims.append({'text':span.excerpt,'evidence':[{'chunk_id':span.chunk_id,'excerpt':span.excerpt}]})
    return GenerationDraft.model_validate({'status':draft.status,'reason':draft.reason,'claims':claims})
