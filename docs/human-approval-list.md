# Human-in-the-Loop Approval Policy

This document defines actions and operations that AI coding agents and automated workflows **must never execute autonomously**. Explicit developer confirmation is required before proceeding.

## 1. High-Risk / Irreversible Actions
The following actions must always be approved by an authorized engineer:
- **Database Schema Migrations & Truncations:** Any command executing `DROP TABLE`, `TRUNCATE`, or destructive data modifications.
- **Git Push to Main / Protected Branches:** Directly pushing to `main` or force-pushing (`git push --force`, `-f`) to any branch.
- **Production Infrastructure Changes:** Deploying or deleting containers, cloud services, or network proxies.
- **Dependency Ingestion:** Adding new third-party packages to `pyproject.toml` or `requirements.txt`.
- **Environment & Secrets Modification:** Creating or altering `.env` configurations or API access tokens.

## 2. Permitted Autonomous Operations
Agents are permitted to perform the following without prior approval:
- Reading project documentation, source files, and test files.
- Executing read-only checks: `git status`, `git diff`, `git log`, `ruff check`.
- Running automated test suites: `make test`, `make test-fast`, `pytest`.
- Editing code files within local feature branches followed by automated test validation.
