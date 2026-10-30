# AI Workflow: Lessons Learned & Gotchas

This document records architectural gotchas and agent failure patterns to prevent repeat mistakes across development sessions.

## 1. Avoid Substring False Positives in Regex Matching
- **Issue:** Regex queries matching tokens without word boundaries caused queries like "Holidays in October" to match "Holi" because "holi" was a substring of "holidays".
- **Rule:** Always use word boundaries (`\b`) when matching entity names and keywords against user queries.

## 2. DuckDB Connection Dictionary Return Formats
- **Issue:** Calling `execute_query("SHOW TABLES")` returned dictionaries (`{'name': 'dim_holiday'}`), causing index lookups `t[0]` to raise `KeyError`.
- **Rule:** When interacting with `LakehouseQueryEngine`, access rows using column keys or `list(row.values())`.

## 3. Vector DB Cache & Invalidation
- **Issue:** Updating relational lakehouse records without invalidating BM25 or vector store instances led to stale responses.
- **Rule:** After running data refresh or Lakehouse builds, reset retriever caches and reload collections.

## 4. Context Budgeting
- **Issue:** Passing entire unstructured documents to local CPU models caused inference timeouts.
- **Rule:** Cap chunk context with FlashRank re-ranking to top candidate slices (budget ~4000 characters).
