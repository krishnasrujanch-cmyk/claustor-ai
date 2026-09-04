"""
Claustor AI — RAG Evaluation Harness
=====================================
Runs golden QA pairs against the RAG pipeline and scores results.

Usage:
  python tests/rag_eval/evaluate.py                    # all tests
  python tests/rag_eval/evaluate.py --category billing  # specific category
  python tests/rag_eval/evaluate.py --id halcyon-ip     # specific test
"""
import asyncio
import json
import sys
import time
from pathlib import Path
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)


async def run_evaluation(filter_category=None, filter_id=None):
    from app.agents.rag.retriever import get_retriever
    from app.infrastructure.vector_store.pinecone_store import embed_query_cohere
    from pinecone import Pinecone
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy import text
    from app.core.config import settings

    # Load test cases
    qa_path = Path(__file__).parent / "golden_qa.json"
    with open(qa_path) as f:
        qa_data = json.load(f)

    test_cases = qa_data["test_cases"]
    if filter_category:
        test_cases = [t for t in test_cases if t["category"] == filter_category]
    if filter_id:
        test_cases = [t for t in test_cases if filter_id in t["id"]]

    engine = create_async_engine(settings.DATABASE_URL)
    retriever = get_retriever()
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    index = pc.Index(host=settings.PINECONE_HOST)

    results = []
    total_retrieval_score = 0
    total_answer_score = 0

    print(f"\n{'='*70}")
    print(f"RAG EVALUATION — {len(test_cases)} test cases")
    print(f"{'='*70}\n")

    for tc in test_cases:
        print(f"--- {tc['id']} ({tc['difficulty']}) ---")
        print(f"  Q: {tc['query']}")

        # 1. RETRIEVAL TEST — check if right chunks are found
        vec = await embed_query_cohere(tc["query"])
        
        # Find contract
        async with AsyncSession(engine) as db:
            r = await db.execute(text(
                "SELECT id FROM contracts WHERE title ILIKE :p AND is_active = true ORDER BY created_at DESC LIMIT 1"
            ), {"p": f"%{tc['contract_pattern']}%"})
            row = r.fetchone()
            if not row:
                print(f"  ❌ Contract '{tc['contract_pattern']}' not found\n")
                continue
            contract_id = str(row[0])

        search_results = index.query(
            namespace="org_00000000",
            vector=vec,
            top_k=20,
            filter={"contract_id": contract_id},
            include_metadata=True, include_values=False,
        )

        # Check if expected content appears in top-20 chunks
        retrieved_texts = [
            m.get("metadata", {}).get("text", "") + " " + m.get("metadata", {}).get("text_preview", "")
            for m in search_results["matches"]
        ]
        all_retrieved = " ".join(retrieved_texts).lower()

        retrieval_hits = 0
        retrieval_total = len(tc["expected_chunks_contain"])
        for expected in tc["expected_chunks_contain"]:
            found = expected.lower() in all_retrieved
            retrieval_hits += int(found)
            status = "✅" if found else "❌"
            print(f"  Retrieval: {status} '{expected}'")

        retrieval_score = retrieval_hits / max(retrieval_total, 1)
        total_retrieval_score += retrieval_score

        # Also accept retrieval pass if context has the facts
        # (chunk text_preview is truncated at 200 chars)

        # 2. ANSWER TEST — run through full RAG pipeline
        async with AsyncSession(engine) as db:
            start = time.time()
            ctx = await retriever.retrieve(
                query=tc["query"],
                org_id=UUID("00000000-0000-0000-0000-000000000002"),
                db=db,
                contract_id=UUID(contract_id),
                plan="enterprise",
            )
            elapsed = time.time() - start

        context_text = ctx.context_text.lower()

        # Check facts in retrieved context
        fact_hits = 0
        fact_total = len(tc["expected_facts"])
        for fact in tc["expected_facts"]:
            found = fact.lower() in context_text
            fact_hits += int(found)
            status = "✅" if found else "❌"
            print(f"  Context:   {status} '{fact}'")

        # Check must_not_contain
        violations = 0
        for bad in tc.get("must_not_contain", []):
            if bad.lower() in context_text:
                violations += 1
                print(f"  Violation: ❌ Contains '{bad}'")

        answer_score = fact_hits / max(fact_total, 1)
        total_answer_score += answer_score

        grade = "PASS" if answer_score >= 0.8 or (retrieval_score >= 0.5 and answer_score >= 0.6) else "FAIL"
        print(f"  Result: {grade} | Retrieval: {retrieval_score:.0%} | Context: {answer_score:.0%} | {elapsed:.1f}s")
        print()

        results.append({
            "id": tc["id"],
            "grade": grade,
            "retrieval_score": retrieval_score,
            "answer_score": answer_score,
            "difficulty": tc["difficulty"],
            "category": tc["category"],
        })

    # Summary
    n = len(results)
    passed = sum(1 for r in results if r["grade"] == "PASS")
    avg_retrieval = total_retrieval_score / max(n, 1)
    avg_answer = total_answer_score / max(n, 1)

    print(f"{'='*70}")
    print(f"SUMMARY: {passed}/{n} PASSED ({passed*100//max(n,1)}%)")
    print(f"  Avg Retrieval Score: {avg_retrieval:.0%}")
    print(f"  Avg Context Score:   {avg_answer:.0%}")
    print(f"{'='*70}")

    # Save results
    out_path = Path(__file__).parent / "eval_results.json"
    with open(out_path, "w") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total": n,
                "passed": passed,
                "avg_retrieval": round(avg_retrieval, 3),
                "avg_answer": round(avg_answer, 3),
            },
            "results": results,
        }, f, indent=2)
    print(f"\nResults saved to {out_path}")

    return passed == n


if __name__ == "__main__":
    category = None
    test_id = None
    for arg in sys.argv[1:]:
        if arg.startswith("--category="):
            category = arg.split("=")[1]
        elif arg.startswith("--id="):
            test_id = arg.split("=")[1]
    
    success = asyncio.run(run_evaluation(category, test_id))
    sys.exit(0 if success else 1)
