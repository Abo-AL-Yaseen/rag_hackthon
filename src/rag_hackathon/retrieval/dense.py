import json
import os
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

import numpy as np
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
import torch

from ..ingestion import corpus_hash
from ..schema import Chunk, Hit


class E5Encoder:
    def __init__(self, model_path, revision, threads=4, batch_size=4):
        self.path = Path(model_path).resolve()
        if not self.path.is_dir():
            raise FileNotFoundError("Approved local E5 cache missing; no automatic download allowed")
        if threads < 1 or batch_size < 1:
            raise ValueError("Positive threads and batch size required")
        torch.set_num_threads(threads)
        self.model = SentenceTransformer(str(self.path), device="cpu", local_files_only=True,
                                         trust_remote_code=False)
        self.model.max_seq_length = 512
        self.revision = revision
        self.batch_size = batch_size
        self.dimension = self.model.get_sentence_embedding_dimension()
        if self.dimension != 384 or self.model.device.type != "cpu":
            raise ValueError("Expected approved 384-dimensional CPU E5-small")

    @property
    def tokenizer(self):
        return self.model.tokenizer

    def _encode(self, texts, prefix):
        if not texts or any(not t.strip() for t in texts):
            raise ValueError("Nonempty texts required")
        inputs = [prefix + t for t in texts]
        if any(len(self.tokenizer(t, add_special_tokens=True)["input_ids"]) > 512 for t in inputs):
            raise ValueError("Input exceeds 512 tokens; chunk or shorten explicitly")
        return self.model.encode(inputs, batch_size=self.batch_size, normalize_embeddings=True,
                                 convert_to_numpy=True, show_progress_bar=False)

    def passages(self, texts):
        return self._encode(texts, "passage: ")

    def queries(self, texts):
        return self._encode(texts, "query: ")


class DenseRetriever:
    collection = "preparation"

    def __init__(self, chunks, encoder, path, *, create=False):
        if not chunks or len({c.chunk_id for c in chunks}) != len(chunks):
            raise ValueError("Unique nonempty chunks required")
        self.encoder = encoder
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        self.manifest_path = path / "retrieval_manifest.json"
        self.manifest = {"corpus_sha256": corpus_hash(chunks), "model_revision": encoder.revision,
                         "dimension": encoder.dimension, "normalization": "l2",
                         "prefixes": {"query": "query: ", "passage": "passage: "}}
        self.client = QdrantClient(path=str(path / "qdrant"))
        try:
            exists = self.client.collection_exists(self.collection)
            if create:
                if exists:
                    raise ValueError("Index already exists; choose a new directory, never silently overwrite")
                self.client.create_collection(self.collection, vectors_config=models.VectorParams(
                    size=encoder.dimension, distance=models.Distance.COSINE))
                vectors = encoder.passages([c.text for c in chunks])
                self.client.upsert(self.collection, points=[models.PointStruct(
                    id=c.chunk_id, vector=v.tolist(), payload=c.payload()) for c, v in zip(chunks, vectors)])
                self.manifest_path.write_text(json.dumps(self.manifest, indent=2))
            elif not exists or not self.manifest_path.exists() or json.loads(self.manifest_path.read_text()) != self.manifest:
                raise ValueError("Missing/incompatible corpus or embedding index; build a new index")
        except Exception:
            self.close()
            raise

    def search(self, question, k=3):
        if k < 1:
            raise ValueError("Positive k required")
        vector = self.encoder.queries([question])[0]
        return self.search_vector(vector, k)

    def search_vector(self, vector, k=3):
        if k < 1 or np.asarray(vector).shape != (self.encoder.dimension,):
            raise ValueError("Positive k and correct vector dimension required")
        points = self.client.query_points(self.collection, query=np.asarray(vector).tolist(),
                                          limit=k, with_payload=True).points
        return [Hit(Chunk(**p.payload), float(p.score)) for p in points]

    def close(self):
        self.client.close()
