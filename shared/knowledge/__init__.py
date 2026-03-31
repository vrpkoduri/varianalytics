"""Knowledge layer -- RAG retrieval, embedding, vector search."""

from shared.knowledge.embedding import EmbeddingService
from shared.knowledge.knowledge_store import KnowledgeStore
from shared.knowledge.rag import Commentary, RAGRetriever
from shared.knowledge.vector_store import (
    InMemoryVectorStore,
    QdrantVectorStore,
    SearchResult,
    VectorStore,
    create_vector_store,
)

__all__ = [
    "EmbeddingService",
    "KnowledgeStore",
    "RAGRetriever",
    "Commentary",
    "VectorStore",
    "InMemoryVectorStore",
    "QdrantVectorStore",
    "SearchResult",
    "create_vector_store",
]
