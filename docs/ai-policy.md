# FiftyFive Technologies — AI Coding & Governance Policy

## 1. Scope & Objective
This policy governs the safe, ethical, and compliant use of AI coding agents across all development activities on ResoAI.

## 2. Approved AI Tooling & Accounts
- Developers must use approved enterprise accounts and authorized tools (Claude Code, OpenAI Codex, Antigravity, Gemini CLI, Cursor).
- Personal accounts must not be used on corporate repositories.
- Local inference models (`llama3.2`, `nomic-embed-text`) running via Ollama are approved for offline/CPU testing.

## 3. Data Classification & Privacy Guardrails
- **Public & Internal Code:** Permitted for agent reasoning.
- **Client & Customer PII:** **Strictly Prohibited.** No live customer records, real financial data, or credentials may be exposed to AI prompts.
- **Test Datasets:** All fixture data and lakehouse records must be synthetically generated (using Faker or masked schemas).

## 4. Dangerous Modes & Prohibitions
- Autonomous bypass flags (such as `--dangerously-skip-permissions` or unrestricted write access) are forbidden outside isolated sandbox containers.
- Agents are blocked from running destructive commands (`rm -rf`, `DROP`, `TRUNCATE`, force-pushes) via `.claude/settings.json` deny rules.

## 5. Code Review & IP Compliance
- All AI-generated code is considered authored by the reviewing engineer.
- Every change must pass peer review and automated CI pipelines before merging to `main`.
- AI attribution must be preserved in commit metadata (`Co-authored-by:` trailer or PR label).

## 6. Review Cadence & Ownership
- **Primary AI Config Owner:** FiftyFive Technologies Core Team (`@Ashu199755tech`)
- **Review Cadence:** AI rules, permissions, and tool configurations are reviewed quarterly.
