"""
Claustor AI — Pinecone Vector Store
Multi-tenant: each org gets its own namespace.
"""

import asyncio
from uuid import UUID

import structlog
from pinecone import Pinecone

from app.core.config import settings

logger = structlog.get_logger(__name__)

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class VectorStore:
    def __init__(self):
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index_name = settings.PINECONE_INDEX
        self._index = None
        self._embedder = None

    @property
    def index(self):
        if self._index is None:
            self._index = self.pc.Index(
                name=self.index_name,
                host=settings.PINECONE_HOST,
            )
        return self._index

    def get_namespace(self, org_id: UUID) -> str:
        return f"org_{str(org_id).replace('-', '')[:8]}"

    async def get_embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            loop = asyncio.get_event_loop()
            self._embedder = await loop.run_in_executor(
                None, lambda: SentenceTransformer(EMBEDDING_MODEL)
            )
        return self._embedder

    async def embed_text(self, text: str) -> list[float]:
        embedder = await self.get_embedder()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: embedder.encode(text, normalize_embeddings=True).tolist()
        )

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        embedder = await self.get_embedder()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: embedder.encode(
                texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False
            ).tolist()
        )

    async def upsert_contract(self, org_id: UUID, contract_id: UUID, chunks: list[dict]) -> int:
        if not chunks:
            return 0
        namespace = self.get_namespace(org_id)
        texts = [c["text"] for c in chunks]
        embeddings = await self.embed_batch(texts)
        vectors = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vectors.append({
                "id": f"{contract_id}_{i}",
                "values": embedding,
                "metadata": {
                    "contract_id": str(contract_id),
                    "org_id": str(org_id),
                    "chunk_index": i,
                    "text": chunk["text"][:1000],
                    "clause_type": chunk.get("clause_type", ""),
                    "page": chunk.get("page", 0),
                },
            })
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, lambda: self.index.upsert(vectors=vectors, namespace=namespace)
        )
        logger.info("contract_indexed", org_id=str(org_id), contract_id=str(contract_id), chunks=len(vectors))
        return len(vectors)

    async def search(self, org_id: UUID, query: str, top_k: int = 6,
                     contract_id: UUID | None = None, clause_type: str | None = None) -> list[dict]:
        namespace = self.get_namespace(org_id)
        query_embedding = await self.embed_text(query)
        filter_dict = {}
        if contract_id:
            filter_dict["contract_id"] = str(contract_id)
        if clause_type:
            filter_dict["clause_type"] = clause_type
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
        return [
            {
                "score": round(m.score, 4),
                "text": m.metadata.get("text", ""),
                "contract_id": m.metadata.get("contract_id"),
                "chunk_index": m.metadata.get("chunk_index", 0),
                "clause_type": m.metadata.get("clause_type", ""),
                "page": m.metadata.get("page", 0),
            }
            for m in results.matches
        ]

    async def delete_contract(self, org_id: UUID, contract_id: UUID) -> None:
        namespace = self.get_namespace(org_id)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.index.delete(
                filter={"contract_id": str(contract_id)},
                namespace=namespace,
            )
        )
        logger.info("vectors_deleted", contract_id=str(contract_id))


_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
