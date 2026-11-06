"""Answer/reference diagnostics and citation audits, not semantic faithfulness."""
from collections import Counter
import re
import unicodedata


def tokens(text):
    text=unicodedata.normalize('NFKC',text).casefold()
    text=re.sub('[\u064b-\u065f\u0670\u0640]','',text)
    return re.findall(r'[^\W_]+',text)


def reference_scores(answer, references):
    if not references or any(not r.strip() for r in references):
        raise ValueError('Nonempty reference answers required')
    a=tokens(answer)
    scores=[]
    for reference in references:
        b=tokens(reference)
        common=sum((Counter(a)&Counter(b)).values())
        f1=2*common/(len(a)+len(b)) if a or b else 1.0
        scores.append({'normalized_exact_match':float(a==b),'token_f1':f1})
    return {key:max(s[key] for s in scores) for key in scores[0]}


def audit_sources(response, retrieved):
    lookup={h.chunk.chunk_id:h.chunk for h in retrieved}
    correct=0
    for source in response.sources:
        c=lookup.get(source.chunk_id)
        correct+=int(c is not None and source.document_id==c.document_id and source.document_name==c.source
                     and source.page_number==c.page and source.version==c.version
                     and bool(source.supporting_excerpt.strip()) and source.supporting_excerpt in c.text)
    source_map={s.source_id:s for s in response.sources}
    quote_claims=sum(all(sid in source_map and claim.text==source_map[sid].supporting_excerpt
                         for sid in claim.source_ids) for claim in response.claims)
    return {'source_references_checked':len(response.sources),'source_references_correct':correct,
            'source_reference_accuracy':correct/len(response.sources) if response.sources else None,
            'claims_checked':len(response.claims),'claims_exactly_copied':quote_claims,
            'semantic_faithfulness':None,
            'note':'Exact-copy and metadata checks do not establish question relevance, entailment or completeness.'}


class RecordingRetriever:
    def __init__(self,retriever):
        self.retriever=retriever
        self.last_hits=[]

    def search(self,question,k):
        self.last_hits=self.retriever.search(question,k)
        return self.last_hits
