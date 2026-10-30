---
name: ai-audit-check
description: Audit the repository against FiftyFive Technologies AI workflow standards. Use when verifying AI governance, permissions, guardrails, and instruction files before merging.
allowed-tools:
  - run_command
  - read_file
---

# AI Workflow Audit Check

Runs automated compliance checks against the repository's AI coding setup.

## Usage
Run the audit check command:
```bash
python -m pytest tests/test_lakehouse.py -v
make lint
```

## Checklist
- [ ] `AGENTS.md` is canonical, concise (<= 200 lines), and contains no secrets.
- [ ] Tool files (`CLAUDE.md`, `.cursorrules`) link to `@AGENTS.md`.
- [ ] Permissions policy in `.claude/settings.json` explicitly denies destructive commands.
- [ ] Personal and sensitive files are ignored via `.gitignore`, `.cursorignore`, and `.geminiignore`.
- [ ] All test data is synthetic; no real PII is present.
- [ ] Pre-commit hooks and GitHub Actions CI pipelines are active.
