# Repository Guidelines

## Project Structure & Module Organization
`backend/app/` contains the FastAPI entrypoint and service layer. `backend/tests/` holds pytest tests, with shared fixtures in `backend/tests/conftest.py`. Reusable infrastructure lives in `shared/` (`db/`, `utils/`, `vector_store/`). Skill-specific workflows, prompts, and helper scripts live under `skills/<skill_name>/`. Use `scripts/` for setup checks and integration tests. `frontend/` is the static demo UI (`index.html`), while `frontend-react/` is the Vite React client with source in `frontend-react/src/`. Runtime artifacts belong in `data/` and `logs/`; verification notes live in `docs/`.

## Build, Test, and Development Commands
Install Python dependencies with `pip install -r backend/requirements.txt`. Start the API with `python backend/run_server.py`; it serves FastAPI on `http://localhost:8000` and writes logs to `logs/patent_api.log`. Run baseline checks with `python scripts/verify_setup.py`. Execute unit tests with `pytest backend/tests -q`. Run `python scripts/test_integration.py` after the server is up. For the React client, use `cd frontend-react && npm install && npm run dev`; build assets with `npm run build`. For the legacy demo, open `frontend/index.html`.

## Coding Style & Naming Conventions
Follow existing Python style: 4-space indentation, snake_case for modules/functions, PascalCase for classes, and short docstrings on non-obvious behavior. Keep service logic in `backend/app/services/` and cross-cutting utilities in `shared/` rather than duplicating code in scripts. In React, use function components, PascalCase page/component filenames (`Home.jsx`), and keep API wrappers in `frontend-react/src/api/`. Frontend lint rules live in `frontend-react/eslint.config.js`; no repo-level Python formatter is configured, so match surrounding code closely.

## Testing Guidelines
Name Python tests `test_*.py` and keep them near the relevant backend/shared behavior in `backend/tests/`. Add or update unit tests for any service, parser, or client change. `pytest-cov` is available, but no minimum threshold is configured; add focused coverage for touched paths. Treat `scripts/test_*.py` as manual checks because some depend on a running server, Selenium, or network access.

## Commit & Pull Request Guidelines
This snapshot does not include `.git`, so local history is unavailable. Use short, imperative commit messages, preferably Conventional Commit style such as `feat(search): add CPC filter support` or `fix(llm): validate missing API key`. Pull requests should summarize the behavior change, list affected areas, include the commands you ran, note any `.env` or data setup changes, and attach screenshots only for UI updates.

## Security & Configuration Tips
Copy `.env.example` to `.env` and keep real API keys out of version control. Do not commit generated database files, vector-store contents, or verbose logs unless they are required to reproduce a bug.
