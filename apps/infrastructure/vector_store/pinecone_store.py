"""
Claustor AI — Pinecone Vector Store
Multi-tenant: each org gets its own namespace.
Org data is physically isolated — one org cannot
query another org's vectors.
"""

import asyncio
from uuid import UUID

import structlog
from pinecone import Pinecone, ServerlessSpec

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Embedding model — must match dimensions in Pinecone index
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384


class VectorStore:
    """
    Pinecone vector store with multi-tenant namespace isolation.

    Namespace per org: org_{org_id_short}
    Example: org_abc12345

    Usage:
        store = VectorStore()
        await store.upsert(org_id, contract_id, chunks)
        results = await store.search(org_id, query_embedding, top_k=6)
    """

    def __init__(self):
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index_name = settings.PINECONE_INDEX
        self._index = None
        self._embedder = None

    @property
    def index(self):
        """Lazy-load index connection."""
        if self._index is None:
            self._index = self.pc.Index(
                name=self.index_name,
                host=settings.PINECONE_HOST,
            )
        return self._index

    def get_namespace(self, org_id: UUID) -> str:
        """
        Get Pinecone namespace for org.
        Format: org_{first 8 chars of org_id}
        Consistent, short, readable.
        """
        return f"org_{str(org_id).replace('-', '')[:8]}"

    async def get_embedder(self):
        """Lazy-load sentence transformer model."""
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            # Run in thread pool — CPU-bound operation
            loop = asyncio.get_event_loop()
            self._embedder = await loop.run_in_executor(
                None,
                lambda: SentenceTransformer(EMBEDDING_MODEL)
            )
            logger.info("embedder_loaded", model=EMBEDDING_MODEL)
        return self._embedder

    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text string."""
        embedder = await self.get_embedder()
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            lambda: embedder.encode(text, normalize_embeddings=True).tolist()
        )
        return embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in one batch — faster than one by one."""
        embedder = await self.get_embedder()
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: embedder.encode(
                texts,
                normalize_embeddings=True,
                batch_size=32,
                show_progress_bar=False,
            ).tolist()
        )
        return embeddings

    async def upsert_contract(
        self,
        org_id: UUID,
        contract_id: UUID,
        chunks: list[dict],
    ) -> int:
        """
        Index contract chunks into Pinecone.

        Args:
            org_id: Organisation ID (determines namespace)
            contract_id: Contract ID (stored in metadata)
            chunks: List of {text, chunk_index, clause_type?, page?}

        Returns:
            Number of vectors upserted
        """
        if not chunks:
            return 0

        namespace = self.get_namespace(org_id)

        # Embed all chunks in one batch
        texts = [c["text"] for c in chunks]
        embeddings = await self.embed_batch(texts)

        # Build vectors for Pinecone
        vectors = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vector_id = f"{contract_id}_{i}"
            metadata = {
                "contract_id": str(contract_id),
                "org_id": str(org_id),
                "chunk_index": i,
                "text": chunk["text"][:1000],  # Pinecone metadata limit
                "clause_type": chunk.get("clause_type", ""),
                "page": chunk.get("page", 0),
            }
            vectors.append({
                "id": vector_id,
                "values": embedding,
                "metadata": metadata,
            })

        # Upsert in batches of 100 (Pinecone limit)
        batch_size = 100
        total_upserted = 0
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda b=batch: self.index.upsert(
                    vectors=b,
                    namespace=namespace,
                )
            )
            total_upserted += len(batch)

        logger.info(
            "contract_indexed",
            org_id=str(org_id),
            contract_id=str(contract_id),
            chunks=total_upserted,
            namespace=namespace,
        )

        return total_upserted

    async def search(
        self,
        org_id: UUID,
        query: str,
        top_k: int = 6,
        contract_id: UUID | None = None,
        clause_type: str | None = None,
    ) -> list[dict]:
        """
        Semantic search within org namespace.
        Optionally filter by contract or clause type.

        Args:
            org_id: Org namespace to search in
            query: Natural language query
            top_k: Number of results to return
            contract_id: Optional — search within specific contract
            clause_type: Optional — filter by clause type

        Returns:
            List of matching chunks with scores
        """
        namespace = self.get_namespace(org_id)

        # Embed query
        query_embedding = await self.embed_text(query)

        # Build metadata filter
        filter_dict: dict = {}
        if contract_id:
            filter_dict["contract_id"] = str(contract_id)
        if clause_type:
            filter_dict["clause_type"] = clause_type

        # Query Pinecone
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: self.index.query(
                vector=query_embedding,
                top_k=top_k,
                namespace=namespace,
                include_metadata=True,
                filter=filter_dict if filter_dict else None,
            )
        )

        # Format results
        chunks = []
        for match in results.matches:
            chunks.append({
                "score": round(match.score, 4),
                "text": match.metadata.get("text", ""),
                "contract_id": match.metadata.get("contract_id"),
                "chunk_index": match.metadata.get("chunk_index", 0),
                "clause_type": match.metadata.get("clause_type", ""),
                "page": match.metadata.get("page", 0),
                "vector_id": match.id,
            })

        logger.debug(
            "vector_search",
            org_id=str(org_id),
            query=query[:50],
            results=len(chunks),
            top_score=chunks[0]["score"] if chunks else 0,
        )

        return chunks

    async def delete_contract(
        self,
        org_id: UUID,
        contract_id: UUID,
    ) -> None:
        """
        Delete all vectors for a contract.
        Called when contract is deleted or reprocessed.
        """
        namespace = self.get_namespace(org_id)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.index.delete(
                filter={"contract_id": str(contract_id)},
                namespace=namespace,
            )
        )

        logger.info(
            "contract_vectors_deleted",
            org_id=str(org_id),
            contract_id=str(contract_id),
        )

    async def get_stats(self, org_id: UUID) -> dict:
        """Get vector count for an org namespace."""
        namespace = self.get_namespace(org_id)
        loop = asyncio.get_event_loop()
        stats = await loop.run_in_executor(
            None,
            lambda: self.index.describe_index_stats()
        )
        ns_stats = stats.namespaces.get(namespace, {})
        return {
            "namespace": namespace,
            "vector_count": getattr(ns_stats, "vector_count", 0),
            "total_index_vectors": stats.total_vector_count,
        }


# Singleton instance
_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """Get or create singleton vector store."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
