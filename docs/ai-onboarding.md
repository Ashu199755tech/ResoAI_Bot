# Developer Onboarding: AI Agent Workflow Setup

Welcome to ResoAI. This guide helps you configure your local development environment for AI pair programming.

## 1. Prerequisites
- Python 3.12+
- Local Ollama instance (`ollama serve`)
- Models pulled:
  ```bash
  ollama pull llama3.2:1b
  ollama pull llama3.2
  ollama pull nomic-embed-text
  ```

## 2. Environment Setup
1. Clone the repository and initialize virtualenv:
   ```bash
   make setup
   ```
2. Verify test execution:
   ```bash
   make test-fast
   ```
3. Initialize the DuckDB Medallion Lakehouse:
   ```bash
   make lakehouse
   ```

## 3. Configuring Your AI Agent
- **Claude Code:** Automatically reads `CLAUDE.md` and enforces permissions in `.claude/settings.json`.
- **Cursor / Windsurf:** Configured via `.cursorrules` and `.cursorignore`.
- **Codex / Gemini / Antigravity:** References canonical guidance in `AGENTS.md`.

## 4. Best Practices
- Keep tasks atomic: formulate a plan first, verify each step with `make test-fast`.
- Run `make lint` before opening pull requests.
- Never paste live passwords, tokens, or PII into chat prompts.
