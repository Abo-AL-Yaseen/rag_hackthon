"""No HTTP server required; Backend injects its initialized retriever/settings."""
from rag_hackathon.generation.providers import provider_from_env
from rag_hackathon.service import RAGService


def make_engine(retriever, *, environment=None, approval=None):
    # Defaults to mock when the selected environment has no LLM_PROVIDER. No call here.
    return RAGService(retriever,provider_from_env(environment,approval=approval))


def answer_json(engine,question,language='en'):
    return engine(question,language=language)
