"""
Backfill party_identifiers for existing analyzed contracts.
Run once: python3 -m app.scripts.backfill_party_identifiers
"""
import asyncio
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from app.core.config import settings

async def backfill():
    from app.infrastructure.identifiers.party_extractor import extract_party_identifiers
    engine = create_async_engine(settings.DATABASE_URL)
    async with AsyncSession(engine) as db:
        # Get contracts needing backfill
        r = await db.execute(text("""
            SELECT id, title, org_id
            FROM contracts
            WHERE status = 'analyzed'
              AND (party_identifiers IS NULL OR party_identifiers = '[]'::jsonb)
            ORDER BY created_at DESC
        """))
        contracts = r.fetchall()
        print(f"Contracts needing backfill: {len(contracts)}")

        for contract in contracts:
            contract_id = str(contract[0])
            title = contract[1]
            try:
                # Get full text from chunks
                r2 = await db.execute(text("""
                    SELECT string_agg(text, ' ' ORDER BY chunk_index)
                    FROM contract_chunks
                    WHERE contract_id = :cid
                """), {"cid": contract_id})
                full_text = r2.scalar() or ""

                if not full_text:
                    print(f"  ⚠️  {title[:40]} — no chunks")
                    continue

                # Extract party identifiers
                party_ids = await extract_party_identifiers(full_text)
                if not party_ids:
                    print(f"  ⚠️  {title[:40]} — no parties found")
                    continue

                # Save to DB
                await db.execute(text("""
                    UPDATE contracts
                    SET party_identifiers = :pids
                    WHERE id = :cid
                """), {"pids": json.dumps(party_ids), "cid": contract_id})
                await db.commit()
                print(f"  ✅ {title[:40]} — {len(party_ids)} parties saved")

            except Exception as e:
                print(f"  ❌ {title[:40]} — {e}")

    print("\nBackfill complete")

if __name__ == "__main__":
    asyncio.run(backfill())
