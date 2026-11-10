# Design — BJT DC Bias Web App (ENG29 2121 · Lab 02)

Date: 2026-11-10
Status: approved 2026-11-10 (student approved after builder check)
Owner: AchisakYam (student) · built with OpenCode + Superpowers

## 1. Intent and why

This is the Lab 02 deliverable for ENG29 2121 (2/2569). The point is not only to
get DC bias numbers, but to demonstrate a real multi-file web application:
a browser form, an HTTP round trip, engineering logic in Python that is separate
from presentation, automated tests, and a Git history on GitHub.

Success = every acceptance item A1–A7 in the lab handout demonstrably passes,
inside one 3-hour lab, with a running `http://127.0.0.1:5000/` demo.

## 2. Goals

- G1. `GET /` returns HTTP 200 with an input form for VCC, R1, R2, RC, RE, β, VBE.
- G2. `POST /calculate` computes the DC operating point **in Python** (no hard-coded
  results in HTML) and renders it back into the same page.
- G3. Outputs carry units and match an independent hand calculation under the same
  forward-active approximation.
- G4. Bad input produces readable, field-specific errors without crashing.
- G5. Results outside the forward-active assumption produce an explicit warning and
  are never presented as trustworthy.
- G6. At least 3 engineering unit tests and at least 1 Flask test-client test.
- G7. A fresh clone can be installed, run, and tested from the README alone.

## 3. Non-goals

- Other bias topologies (fixed, emitter, collector feedback).
- SPICE/ngspice, DC load line, AC small-signal, gain, Bode, transient, signal generator.
- Interactive schematic, overlay animation, FET.
- User accounts, database, deployment, Docker.
- CSS frameworks, JavaScript build tooling, charting libraries.

## 4. Anti-goals (failures even if the page “works”)

- Numbers computed in Jinja/JavaScript or copy-pasted from the handout.
- MCU-style “it runs” without tests, or tests that assert hard-coded strings
  instead of engineering values.
- A page that shows a confident answer while the model assumption is violated.
- An unhandled exception (500) on non-numeric or missing input.
- Committing `.venv/`, `__pycache__/`, secrets, or the entire virtual environment.

## 5. Constraints

- Time: 75 minutes of build time in a 180-minute lab.
- Environment: Windows, OpenCode Desktop 2.2.6, Python 3.15.2 (`python` on PATH),
  Git 2.56, GitHub Desktop 3.6.10. Flask is installed into a local `.venv` only.
- Model: NPN common-emitter, voltage-divider bias, forward-active approximation,
  constant β and constant VBE. Not a SPICE solver.
- Repo: `C:\Users\b6821654\Documents\GitHub\BJT DC Bias Web App`
  (local `main`, initial commit exists, no remote yet → must be published public).
- Commits are made by the student through **GitHub Desktop**, not by CLI.

## 6. Approaches considered

| # | Approach | Trade-off | Verdict |
|---|----------|-----------|---------|
| A | `GET /` + `POST /calculate`, engineering logic in `dc_bias.py`, Jinja renders results | Two routes, sticky form values needed; clean separation and easy to test at two levels | **Chosen** |
| B | Single `GET/POST /` route | Shortest code; muddier frontend/backend story and weaker route-level tests | Rejected |
| C | JSON API + `fetch` in the browser | Modern split, but adds JS, JSON contract, client-side error handling and ~30–45 min of extra work/risk | Rejected |

## 7. Decisions

### 7.1 Input model

| Field | Unit accepted | Stored as | Rule |
|-------|---------------|-----------|------|
| VCC | V | float | `> 0` |
| R1, R2 | kΩ | ×1000 → Ω | `> 0` |
| RC, RE | kΩ | ×1000 → Ω | `> 0` |
| β | — | float | `> 0` (also `≥ 1` warning-free; values below 1 are rejected as non-physical) |
| VBE | V | float | `0 < VBE < VCC` |

Inputs are kΩ for resistors because that is how the lab sheet and real datasheets
present them; the conversion happens once, inside a `dc_bias.py` parse helper, and
the UI label must say `kΩ`. Boundary rule: `calculate()` accepts SI units only
(Ω and V), so the engineering function never depends on the form's unit choice. Default values in the form: `VCC=12`, `R1=100`, `R2=22`, `RC=2.2`,
`RE=1`, `β=100`, `VBE=0.70`.

### 7.2 Calculation (single source of truth, `dc_bias.py`)

```
VTH = VCC·R2/(R1+R2)
RTH = R1·R2/(R1+R2)
IB  = (VTH − VBE) / (RTH + (β+1)·RE)
IC  = β·IB
IE  = (β+1)·IB
VE  = IE·RE
VB  = VE + VBE
VC  = VCC − IC·RC
VCE = VC − VE
```

Returns a frozen dataclass `BiasResult` with SI values plus `vth`, `rth` and a
`region` enum: `ACTIVE`, `CUTOFF`, `SATURATION`, `INVALID`.

Signature (SI units only):

```python
def calculate(vcc, r1, r2, rc, re, beta, vbe) -> BiasResult:  # V, Ω, Ω, Ω, Ω, —, V
def parse_form(raw: dict[str, str]) -> tuple[BiasInputs, list[str]]:  # kΩ → Ω + errors
```

### 7.3 Region logic

- `CUTOFF` when `VTH ≤ VBE` (base-emitter not forward biased → IB, IC ≈ 0).
  Report currents as 0, warn that the transistor is off.
- `SATURATION` when `VCE ≤ 0.3 V` (including negative VCE). Report the computed
  numbers but label them **unreliable**; the forward-active equations no longer hold.
- `ACTIVE` otherwise.
- `INVALID` only for numerically impossible results (e.g. non-finite), which should
  be unreachable after validation but must not crash the page.

### 7.4 Validation and error behaviour

- Missing, empty, or non-numeric field → error message naming the field.
- `VCC`, resistors, β `≤ 0` → error; `VBE` outside `(0, VCC)` → error.
- On error the route re-renders the form with **HTTP 200**, keeps the user's raw text,
  shows an error panel, and performs **no** calculation.
- No traceback, no 500, for any user-supplied string.

### 7.5 Presentation

- One page: form on top, results panel below, error/warning panels between.
- Units shown for every number: V, mA, µA, kΩ.
- Precision: voltages 3 decimals, currents 3 decimals, β as entered.
- Show the intermediate `VTH` and `RTH` so the grader can follow the working.
- Show `IB`, `IC`, `IE` (A6 rubric asks for units; showing all three is cheap).
- `static/style.css` only, no framework; must remain readable on a phone-width window.
- Server-rendered HTML only (no client-side calculation anywhere).

### 7.6 File layout (matches the handout)

```
app.py                    # Flask app factory + routes
dc_bias.py                # dataclass, validation helpers, equations
templates/index.html      # form + results + error/warning panels
static/style.css
tests/test_dc_bias.py     # engineering unit tests
tests/test_web.py         # Flask test client tests
requirements.txt          # Flask (pinned)
README.md                 # install, run, test, model limits
AGENTS.md                 # conventions for AI-assisted edits
docs/design-note.md
docs/validation.md        # hand calculation + tolerance table
docs/reflection.md
.gitignore
```

### 7.7 Tests (unittest, runnable exactly as the handout says)

`python -m unittest discover -s tests -v`

- `test_dc_bias.py`
  1. Reference case matches hand calculation (VCC=12, R1=100k, R2=22k, RC=2.2k,
     RE=1k, β=100, VBE=0.7): VB 1.942 V, VE 1.242 V, VC 9.294 V, VCE 8.052 V,
     IC 1.230 mA, region ACTIVE. Tolerance ±0.01 V / ±0.01 mA.
  2. kΩ→Ω conversion: `parse_form()` with kΩ values produces the same result as
     `calculate()` fed the equivalent Ω values directly.
  3. Cutoff: VTH ≤ VBE (e.g. R2 small) → region CUTOFF, IC ≈ 0.
  4. Saturation: RC large / VCC low → region SATURATION and a warning string.
  5. Validation: R1 = 0, β = 0, VBE ≥ VCC, non-numeric → raises the documented error.
- `test_web.py`
  1. `GET /` → 200 and contains all seven input names.
  2. `POST /calculate` with the reference case → 200, contains `1.942`, `9.294`,
     `1.230`, and `Active`.
  3. `POST /calculate` with `R1=0` → 200, shows an error, shows no VCE value.

### 7.8 Docs

- `README.md`: what it is, requirements, venv + install + run + test commands,
  the reference result, and a clear statement of model limits (forward active only).
- `docs/validation.md`: hand calculation with intermediate values, tolerance, and
  the two out-of-region cases.
- `docs/reflection.md`: answers to the four individual questions in the handout:
  1. Why is opening `templates/index.html` directly not the same as running Flask?
  2. How does the form send data to Python?
  3. If an equation in `dc_bias.py` changes, must the HTML change?
  4. Why must results outside the model's valid region carry a warning?
- `AGENTS.md`: where logic lives, never compute in templates, tests required,
  kΩ at the boundary only, no secrets committed.

## 8. Left to the builder

- Exact HTML structure/markup and CSS styling (lab allows any layout).
- Helper names and internal decomposition inside `dc_bias.py`.
- Whether validation raises a custom exception or returns an error list, as long as
  `test_dc_bias.py` can assert the documented behaviour.
- Exact wording of error/warning text (must name the field and the violated rule).
- Flask version pin, within Flask 3.x.
- Whether `app.py` uses an app factory (`create_app()`) — tests must work either way.

## 9. Acceptance mapping

| Item | How this design satisfies it |
|------|------------------------------|
| A1 GET / | Route + template + test_web 1 |
| A2 POST calculate | Route calls `dc_bias.calculate()`, values rendered from the result object |
| A3 Engineering reference | Section 7.2/7.7 tolerance test + `docs/validation.md` |
| A4 Validation | Section 7.4 + tests 5 and test_web 3 |
| A5 Outside active region | Section 7.3 + tests 3, 4 and warning panel |
| A6 Unit + HTTP tests | 5 engineering tests + 3 Flask-client tests, `unittest discover` |
| A7 GitHub reproducibility | README, requirements.txt, .gitignore; verified by fresh-clone check |

## 10. Commit plan (GitHub Desktop only)

1. Student publishes the repo **public** in GitHub Desktop (no remote yet).
2. Commit 1: scaffold + `dc_bias.py` + engineering tests + `.gitignore` + `requirements.txt`
   + design/plan docs.
3. Commit 2: Flask routes + template + CSS + web tests.
4. Commit 3: README, `AGENTS.md`, validation notes, reflection.
5. Each commit: student ticks files, writes the summary, clicks Commit, then Push.
6. Agent verifies afterwards with read-only `git log` / `git status` only.
