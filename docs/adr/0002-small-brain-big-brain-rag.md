# ADR 0002: Small Brain / Big Brain Tiered Inference Architecture

## Status
Accepted

## Context
Running large LLMs locally on CPU for both query routing and document synthesis causes unacceptably high latency (often > 120s per request). Additionally, hardcoded regex intent matching is brittle across colloquial employee queries.

## Decision
We decouple inference into a two-tier strategy:
1. **The Small Brain (`llama3.2:1b`):** Fast query decomposition (< 2s on CPU). Parses natural language into structured JSON `QueryPlan` extracting intent, entity (`employee`, `project`, `holiday`, `policy`), and selective search terms.
2. **Deterministic Fast Path:** Quantitative queries route directly to the DuckDB Lakehouse without calling synthesis models.
3. **The Big Brain (`llama3.2`):** Reserved for nuanced semantic retrieval, cross-document comparison, and factual synthesis using FlashRank cross-encoder re-ranking.

## Consequences
- **Positive:** Reduces average query latency from > 120s to < 10s on CPU; eliminates brittle regex matching.
- **Negative:** Requires local availability of both `llama3.2:1b` and `llama3.2` models in Ollama.
