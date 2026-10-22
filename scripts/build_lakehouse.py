#!/usr/bin/env python3
"""Build and populate the DuckDB Medallion Lakehouse and sync to Vector Store."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.lakehouse.pipeline import LakehousePipeline
from src.lakehouse.query_engine import LakehouseQueryEngine


def main():
    parser = argparse.ArgumentParser(description="ResoAI Medallion Lakehouse Builder")
    parser.add_argument("--count", type=int, default=500, help="Number of synthetic employee records to generate")
    parser.add_argument("--sync-vector", action="store_true", help="Sync Gold records to ChromaDB vector store")
    args = parser.parse_args()

    print("=" * 70)
    print("🏗️  BUILDING RESOAI MEDALLION LAKEHOUSE (DUCKDB)")
    print("=" * 70)

    start = time.monotonic()
    pipeline = LakehousePipeline()

    # Step 1: Bronze
    print("\n🥉 Step 1/3: Ingesting Raw Data to Bronze Layer...")
    bronze_file = pipeline.ingest_bronze(record_count=args.count)
    print(f"   Saved raw JSON: {bronze_file}")

    # Step 2: Silver
    print("\n🥈 Step 2/3: Transforming & Conforming to Silver Layer...")
    silver_stats = pipeline.process_silver(bronze_file)
    print(f"   Cleaned & Deduplicated: {silver_stats}")
    print(f"   Parquet exports saved in: {pipeline.silver_dir}")

    # Step 3: Gold
    print("\n🥇 Step 3/3: Constructing Gold Star Schema & Business Marts...")
    gold_stats = pipeline.process_gold()
    print(f"   Star Schema Built: {gold_stats}")
    print(f"   DuckDB Persistent Database: {pipeline.db_path}")

    # Optional: Sync to Vector Store
    if args.sync_vector:
        print("\n🔄 Syncing Gold Records to ChromaDB Vector Store...")
        try:
            from src.lakehouse.vector_sync import sync_lakehouse_to_vector_store
            synced_count = sync_lakehouse_to_vector_store(pipeline, limit=50)
            print(f"   Successfully embedded {synced_count} profiles in ChromaDB!")
        except Exception as e:
            print(f"   ⚠️ Vector sync skipped/deferred: {e}")

    # Step 4: Verification Queries
    print("\n⚡ Verifying DuckDB Analytical Queries:")
    engine = LakehouseQueryEngine(str(pipeline.db_path))

    q1 = "How many employees are in HR?"
    res1 = engine.query_smart(q1)
    if res1:
        print(f"\n   Q: {q1}")
        print(f"   A: {res1['summary']}")
        print(f"   Execution time: {res1['time_elapsed']}s")

    q2 = "Average salary in Artificial Intelligence"
    res2 = engine.query_smart(q2)
    if res2:
        print(f"\n   Q: {q2}")
        print(f"   A: {res2['summary']}")
        print(f"   Execution time: {res2['time_elapsed']}s")

    q3 = "Department summary"
    res3 = engine.query_smart(q3)
    if res3:
        print(f"\n   Q: {q3}")
        print(f"   A: {res3['summary']}")

    elapsed = time.monotonic() - start
    print("\n" + "=" * 70)
    print(f"✅ Medallion Lakehouse Build Completed in {elapsed:.2f} seconds!")
    print("=" * 70)


if __name__ == "__main__":
    main()
