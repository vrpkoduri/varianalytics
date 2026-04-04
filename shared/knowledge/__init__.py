"""Knowledge layer -- RAG retrieval, embedding, vector search, knowledge graph."""

from shared.knowledge.embedding import EmbeddingService
from shared.knowledge.graph_builder import (
    build_variance_graph,
    build_variance_graph_from_data,
)
from shared.knowledge.graph_interface import VarianceGraph
from shared.knowledge.knowledge_store import KnowledgeStore
from shared.knowledge.networkx_graph import NetworkXGraph
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
    # Knowledge Graph (Phase 3A)
    "VarianceGraph",
    "NetworkXGraph",
    "build_variance_graph",
    "build_variance_graph_from_data",
]
