import re
import unicodedata

from rank_bm25 import BM25Okapi

from ..schema import Hit


def tokenize(text):
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"[\u064b-\u065f\u0670\u0640]", "", text)
    text = text.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"}))
    return re.findall(r"[^\W_]+", text, flags=re.UNICODE)


class BM25Retriever:
    def __init__(self, chunks):
        if not chunks or not any(tokenize(c.text) for c in chunks):
            raise ValueError("BM25 requires nonempty tokenized chunks")
        self.chunks = chunks
        self.index = BM25Okapi([tokenize(c.text) for c in chunks])

    def search(self, question, k=3):
        if k < 1 or not question.strip():
            raise ValueError("Nonempty question and positive k required")
        scores = self.index.get_scores(tokenize(question))
        order = sorted(range(len(scores)), key=lambda i: (-scores[i], self.chunks[i].chunk_id))
        # Zero-overlap results are not lexical evidence. No universal semantic refusal implied.
        return [Hit(self.chunks[i], float(scores[i])) for i in order[:k] if scores[i] > 0]
