# Changelog

## Unreleased (2026-11-01)

- Added a trusted-publishing workflow (`.github/workflows/publish.yml`) for PyPI — no API token stored in the repo.

- Fixed tests so they pass from any working directory (task path is now built from the test file, not from the current folder). 19 tests passing from any folder.
- Added CONTRIBUTING.md and a bug-report template.
- Added a demo video (`demo.mp4`): a real terminal run of `extracteval run tasks/invoices.yaml` with the mock provider, no API key.
- Added a link to the live browser demo on the portfolio site.

## 0.1.0 — 2026-09-30

- Restored the leaderboard print in `extracteval compare`, with a regression test.
- Added `--version` to the CLI.
- Test suite: 19 tests passing.

## Earlier

- Schema-driven extraction tasks in YAML, type-aware scoring, multi-model leaderboard, supervisor routing, CLI and dashboard.
- No releases were tagged before 0.1.0, so earlier changes are not listed by date here.
