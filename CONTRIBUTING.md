# Contributing guide

Thank you for your interest in improving StockFlow. This project prioritizes small, verifiable changes that directly support inventory management.

## Set up the project

1. Create a descriptive branch from `main`, such as `feature/csv-import` or `fix/stock-transfer`.
2. Create and activate a Python virtual environment.
3. Install development dependencies:

   ```bash
   python -m pip install -r requirements-dev.txt
   ```

4. Copy `.env.example` to `.env` and prepare PostgreSQL as described in the README.
5. Apply database migrations with `alembic upgrade head`.

## Change guidelines

- Use English for code, models, fields, endpoints, technical documentation, and repository metadata.
- Keep the current end-user interface and validation feedback in Spanish.
- Never update inventory directly; every quantity change must be represented by a movement.
- Preserve movement history and references to inactive products and locations.
- Avoid new dependencies or layers when the standard library or existing structure is sufficient.
- Never commit `.env`, credentials, local databases, or real business data.

## Tests

Run the complete suite before opening a pull request:

```bash
pytest
```

Add tests for every new business rule or bug fix. If a model changes, include and review the corresponding Alembic migration.

## Pull requests

Explain the problem, the implementation decision, and how the result was verified. Include screenshots for visual changes. Keep each pull request focused on a single objective so it remains easy to review.
