# Contributing

SyncCart AI is structured as a Python backend/Vision workspace plus a React/TypeScript frontend monorepo.

## Engineering rules

1. Preserve backward-compatible API behavior unless a documented migration is required.
2. Add or update tests with every behavior change.
3. Do not place camera loops, model inference, or other long-running work inside API request handlers.
4. Keep secrets in environment variables; never commit `.env`.
5. Use UTC timestamps internally.
6. Avoid biometric identity and demographic inference.
7. Preserve idempotency for customer and physical-event mutations.
8. Do not represent unmeasured model metrics as achieved performance.
9. Keep raw captures, generated datasets, local databases, and model weights outside Git.
10. Document architecture changes with an ADR when they alter system boundaries.

## Before commit

Python/source verification:

```powershell
python scripts\verify_submission.py
pytest -q
```

Recommended linting when development dependencies are installed:

```powershell
ruff check .
```

Frontend verification after `npm install`:

```powershell
npm run typecheck
npm run build
```

## Branch naming

- `feature/<name>`
- `fix/<name>`
- `refactor/<name>`
- `docs/<name>`

## Pull-request expectations

A change should explain:

- what behavior changed;
- why the change is required;
- how it was tested;
- whether API/event contracts changed;
- whether privacy/security assumptions changed;
- whether model/data assumptions changed.
