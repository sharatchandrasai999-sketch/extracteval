# Contributing

Thanks for helping. This is a small, personal project, so keep changes small and easy to review.

## Before you send a change

- Run the tests from any folder: `pytest -q` (tests must not depend on the current working directory)
- Keep the no-key path working: `extracteval run tasks/invoices.yaml` must work with the mock provider, no API key, and no download.
- If you add a task, ship its YAML file and its labelled data with it, so a stranger can run it.

## Reporting a problem

Open an issue and include:

- The exact command you ran
- The task file, if it is about a task
- What happened, and what you expected instead

Do not include API keys, private documents, or personal details.
