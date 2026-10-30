---
name: build-lakehouse
description: Build the DuckDB Medallion Lakehouse (Bronze -> Silver -> Gold) and synchronize holiday tables into ChromaDB. Use when refreshing data models or updating company records.
disable-model-invocation: true
allowed-tools:
  - run_command
  - read_file
---

# Build Lakehouse Workflow

Rebuilds the DuckDB Star Schema and dual-syncs to the ChromaDB vector database.

> [!WARNING]
> This command refreshes analytical tables and syncs embeddings. Run only with developer confirmation.

## Usage
Run with the default configuration:
```bash
make lakehouse
```
Or execute with custom record count:
```bash
python scripts/build_lakehouse.py --count 500 --sync-holidays
```

## Verification
Verify table creation and queries:
1. Confirm `data/lakehouse/resoai_lakehouse.duckdb` exists.
2. Confirm `company_holidays` and `fact_employee_allocations` tables are populated.
3. Run `make test-fast` to verify analytical queries return successfully.
