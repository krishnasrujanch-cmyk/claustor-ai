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
EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"
_EMBEDDER_CACHE = None  # Module-level cache — survives across instances
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
        """Lazy-load sentence transformer model — module-level cache."""
        global _EMBEDDER_CACHE
        if _EMBEDDER_CACHE is None:
            from sentence_transformers import SentenceTransformer
            loop = asyncio.get_event_loop()
            import os
            cache_dir = os.getenv("SENTENCE_TRANSFORMERS_HOME", 
                       os.path.expanduser("~/.cache/huggingface/sentence_transformers"))
            _EMBEDDER_CACHE = await loop.run_in_executor(
                None,
                lambda: SentenceTransformer(EMBEDDING_MODEL, cache_folder=cache_dir, local_files_only=True)
            )
            logger.info("embedder_loaded", model=EMBEDDING_MODEL)
        self._embedder = _EMBEDDER_CACHE
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

    async def delete_contract_family(self, org_id: UUID, family_id: UUID) -> None:
        """Delete all vectors for a contract family (before indexing new version)."""
        try:
            namespace = self.get_namespace(org_id)
            loop = asyncio.get_event_loop()
            # Pinecone delete by metadata filter
            await loop.run_in_executor(
                None,
                lambda: self.index.delete(
                    filter={"family_id": str(family_id)},
                    namespace=namespace,
                )
            )
            logger.info("contract_family_deleted", family_id=str(family_id))
        except Exception as e:
            logger.warning("contract_family_delete_failed", error=str(e))

    async def upsert_contract(
        self,
        org_id: UUID,
        contract_id: UUID,
        chunks: list[dict],
        family_id: UUID | None = None,
        version_number: int = 1,
    ) -> int:
        """
        Index contract chunks into Pinecone.

        Args:
            org_id: Organisation ID (determines namespace)
            contract_id: Contract ID (stored in metadata)
            chunks: List of {text, chunk_index, clause_type?, page?}
            family_id: Root contract ID for version family
            version_number: Version number (1, 2, 3...)

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
                "contract_id":    str(contract_id),
                "family_id":      str(family_id or contract_id),
                "org_id":         str(org_id),
                "chunk_index":    i,
                "version_number": version_number,
                "text":           chunk["text"][:1000],
                "clause_type":    chunk.get("clause_type", ""),
                "page":           chunk.get("page", 0),
                "contract_title": chunk.get("contract_title", ""),
                "counterparty":   chunk.get("counterparty", ""),
                "contract_value": chunk.get("contract_value", ""),
            }
            vectors.append({
                "id": vector_id,
                "values": embedding,
                "metadata": metadata,
            })

        # Upsert in concurrent batches of 100 (Pinecone limit)
        # Run up to 3 batches concurrently for 3x throughput
        batch_size = 100
        max_concurrent = 3
        total_upserted = 0
        loop = asyncio.get_event_loop()
        batches = [vectors[i:i+batch_size] for i in range(0, len(vectors), batch_size)]

        for chunk_start in range(0, len(batches), max_concurrent):
            concurrent_batches = batches[chunk_start:chunk_start+max_concurrent]
            tasks = [
                loop.run_in_executor(
                    None,
                    lambda b=batch: self.index.upsert(
                        vectors=b,
                        namespace=namespace,
                    )
                )
                for batch in concurrent_batches
            ]
            await asyncio.gather(*tasks)
            total_upserted += sum(len(b) for b in concurrent_batches)
            logger.debug("pinecone_batch_upserted",
                        batch_count=len(concurrent_batches),
                        total_so_far=total_upserted)

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
