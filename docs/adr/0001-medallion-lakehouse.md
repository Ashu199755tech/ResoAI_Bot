# ADR 0001: Adoption of DuckDB Medallion Lakehouse for Structured Analytics

## Status
Accepted

## Context
ResoAI requires 100% accurate quantitative answers for internal enterprise queries (e.g., headcount counts, department staffing, project allocations, salary analytics, and company holidays). Traditional vector search on unstructured chunks introduces hallucination risk and probabilistic inaccuracy for numerical aggregation.

## Decision
We implement a Medallion Architecture using an embedded DuckDB database:
1. **Bronze Layer:** Raw unmodified JSON ingestion with timestamp audit metadata (`data/lakehouse/bronze/`).
2. **Silver Layer:** Cleaned, typed, conformed tables exported to compressed Parquet format (`data/lakehouse/silver/`).
3. **Gold Layer:** Star Schema with Dimension tables (`dim_employee`, `dim_department`, `dim_project`, `dim_holiday`), Fact table (`fact_employee_allocations`), and Analytical Mart views (`company_holidays`, `gold_dept_summary`, `gold_city_headcount`, `gold_project_staffing`).
4. **Dual-Sync Bridge:** High-dimensional semantic profiles synced into ChromaDB for conceptual retrieval alongside deterministic SQL execution.

## Consequences
- **Positive:** Sub-millisecond analytical execution, zero hallucinations for counts/sums, and Parquet storage portability.
- **Negative:** Requires background synchronization between relational data and vector embeddings.
