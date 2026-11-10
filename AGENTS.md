# AGENTS.md — working rules for this repository

Conventions for any AI-assisted change (OpenCode, Copilot, etc.) and for the human
maintainer.

## Architecture

- `dc_bias.py` is the only place where engineering math lives. It must not import
  Flask, Jinja or anything HTTP-related.
- `app.py` handles HTTP only: read the form, call `dc_bias`, choose the template.
- `templates/` and `static/` handle presentation only. Never compute physics in a
  template or in JavaScript.
- `tests/` mirrors the two layers: engineering tests and Flask test-client tests.

## Units

- The web form accepts **kΩ** for R1, R2, RC, RE.
- kΩ → Ω conversion happens only in `dc_bias.parse_form`.
- `dc_bias.calculate` accepts SI units only (Ω, V) and returns SI units.
- Every displayed value must carry a unit.

## Behaviour

- Validation errors are returned with HTTP 200 and a message that names the field.
  Never let bad input produce a 500.
- Results outside the forward-active region (`VTH ≤ VBE`, `VCE ≤ 0.3 V`) must carry a
  warning and must not be described as accurate.

## Tests

- Every behaviour change needs a test that failed first.
- Run the whole suite before claiming success:
  `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
- Do not weaken or delete a test to make a change pass.

## Git and secrets

- Never commit `.venv/`, `__pycache__/`, `.env`, API keys or credentials.
- Commits are created in **GitHub Desktop** by the student; agents must not run
  `git add`, `git commit` or `git push` in this repository.
- Keep commit messages focused on one change.
