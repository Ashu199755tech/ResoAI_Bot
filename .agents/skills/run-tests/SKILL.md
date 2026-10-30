---
name: run-tests
description: Run the automated test suite and code quality checks for ResoAI. Use when verifying code changes, validating the lakehouse pipeline, or preparing a pull request.
allowed-tools:
  - run_command
  - read_file
---

# Run Tests Workflow

Execute the verification pipeline for ResoAI.

## Usage
Run targeted tests or the full test suite:
- Fast unit tests: `make test-fast`
- Code linting: `make lint`
- Full test suite: `make test`

## Steps
1. **Lint Check:**
   Run `make lint` to confirm there are no style or syntax violations.
2. **Fast Unit Tests:**
   Run `make test-fast` to test Lakehouse models, Star Schema, and query engine.
3. **Full Regression:**
   Run `make test` for end-to-end RAG and bot tests.

## Verification
Ensure all test cases output `PASSED` and the command exits with code 0 before marking the task complete.
