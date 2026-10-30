# ResoAI — Agent Instruction Guide

> Canonical AI agent instructions for ResoAI. Single source of truth across all AI tools.

## 1. Project Overview & Architecture
ResoAI is an enterprise Conversational RAG assistant built with an autonomous Self-Correcting Agentic CRAG pipeline and DuckDB Medallion Lakehouse.
- **Architecture Details:** See [ARCHITECTURE.md](ARCHITECTURE.md) and [PROCESS_ARCHITECTURE.md](PROCESS_ARCHITECTURE.md).
- **Setup & API Documentation:** See [README.md](README.md).
- **AI Policy & Governance:** See [docs/ai-policy.md](docs/ai-policy.md).

## 2. Directory Map ("Where to Find What")
- `src/main.py`: FastAPI server entrypoint and `/api/ask`, `/api/debug`, `/api/health` routes.
- `src/config.py`: Centralized Pydantic application settings.
- `src/rag/`: Retrieval-Augmented Generation pipeline.
  - `chain.py`: Hybrid search (BM25 + Vector + FlashRank) and generation.
  - `data_interpreter.py`: Deterministic entity counter and JSON scanner.
  - `query_decomposer.py`: Small-brain LLM intent parser (`llama3.2:1b`).
- `src/lakehouse/`: DuckDB Medallion Lakehouse architecture.
  - `pipeline.py`: Bronze -> Silver -> Gold transformation pipeline.
  - `query_engine.py`: Sub-millisecond analytical query engine for Gold Star Schema.
  - `vector_sync.py`: Dual-sync bridge between DuckDB Gold tables and ChromaDB.
- `data/`: Source-of-truth JSONs, DuckDB database (`data/lakehouse/`), and ChromaDB store.
- `scripts/`: Executable runners (`run_web.py`, `build_lakehouse.py`).
- `tests/`: Automated unit and integration test suite.

## 3. Development Commands (Headless & Deterministic)
All commands run without interactive prompts:
```bash
# Testing
make test                   # Full test suite (pytest -v)
make test-fast              # Fast targeted test: pytest tests/test_lakehouse.py -v
pytest tests/test_lakehouse.py -k "test_lakehouse_query_engine"  # Single targeted test

# Linting & Code Quality
make lint                   # Check code quality with Ruff
make format                 # Auto-format with Ruff

# Lakehouse & Data Ingestion
make lakehouse              # Build DuckDB Bronze/Silver/Gold & sync holidays

# Run Server
make run                    # Launch web chatbot server on port 8000
```

## 4. Model & Inference Guidelines
- **Small Brain (Decomposer):** `llama3.2:1b` (low CPU latency, extracts intent & search terms).
- **Big Brain (Synthesis):** `llama3.2` with temperature 0.1 for strict factual fidelity.
- **Analytical Queries:** Deterministic routing to DuckDB Gold Star Schema (`LakehouseQueryEngine`) for headcounts, salaries, and company holidays.

## 5. Security Guardrails & Safe Execution
- **Strictly Prohibited:** `rm -rf`, force-push (`git push -f`), `DROP TABLE`, `TRUNCATE`, modifying `.env`, or downloading unverified remote binaries (`curl ... | sh`).
- **Secrets:** Never log or commit credentials, API keys, or production tokens. Keep `.env` gitignored.
- **Approval Points:** Production deployments, dependency additions, and schema migrations require human confirmation (see [docs/human-approval-list.md](docs/human-approval-list.md)).

## 6. Context & Session Hygiene
- Keep session context lean: plan large modifications first, verify step-by-step with `make test-fast`.
- Compact or refresh the conversation session when switching between unrelated tasks.
- Keep `AGENTS.md` concise (< 200 lines); offload domain policies to [docs/](docs/).
