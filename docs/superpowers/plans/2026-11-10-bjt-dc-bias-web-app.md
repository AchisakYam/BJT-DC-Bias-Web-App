# BJT DC Bias Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Lab 02 Flask web app that computes the BJT common-emitter voltage-divider DC operating point and passes acceptance items A1–A7.

**Architecture:** One Flask app (`app.py`) with two routes calls a pure-Python engineering module (`dc_bias.py`) that owns parsing, validation, region classification and the equations. Jinja renders one page (`templates/index.html`) with a form, an error panel, a warning panel and a results table; `static/style.css` styles it. `unittest` covers both the engineering module and the HTTP routes.

**Tech Stack:** Python 3.15, Flask 3.x, Jinja2, unittest, plain CSS.

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-dc-bias-design.md`

## Global Constraints

- Resistor inputs arrive in **kΩ** and are converted to **Ω** exactly once, in `dc_bias.parse_form`. `dc_bias.calculate` accepts SI units only.
- No calculation in HTML, Jinja or JavaScript. Every displayed number comes from `BiasResult`.
- `GET /` must return 200; `POST /calculate` must return 200 for both success and validation failure (never 500).
- Region thresholds: `CUTOFF` when `VTH <= VBE`; `SATURATION` when `VCE <= 0.3`; otherwise `ACTIVE`.
- Display precision: 3 decimals for V, mA and µA.
- Tests run with `python -m unittest discover -s tests -v` from the repo root.
- **Commits are made by the student in GitHub Desktop.** The agent must never run `git commit`, `git add` or `git push`. After a task's checks pass, stop and hand over to the student, then verify with read-only `git log`/`git status`.
- Keep scope to DC bias only: no SPICE, AC, transient, charts, JS, Docker or database.

## Review Focus

- **Non-numeric and empty input** — the page must show a field-named error and still return 200, not crash.
- **Values that pass validation but break the model** — VBE close to VTH (near-cutoff) and VCE near 0.3 V (near-saturation) must be classified correctly on both sides of the boundary.
- **Unit confusion** — the same physical circuit entered in kΩ must produce identical results to the Ω form the engineering function takes.
- **Unusual numeric formats** — scientific notation and surrounding whitespace accepted; thousands separators and comma decimals rejected with a readable error.
- **Minimum β (1)** — must compute finite currents without division surprises.

---

### Task 1: Engineering core, validation, and unit tests

**Files:**
- Create: `dc_bias.py`
- Create: `tests/__init__.py` (empty)
- Create: `tests/test_dc_bias.py`
- Create: `requirements.txt`
- Create: `.gitignore`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `Region(str, Enum)` with members `ACTIVE = "active"`, `CUTOFF = "cutoff"`, `SATURATION = "saturation"`, `INVALID = "invalid"`.
  - `BiasInputs` frozen dataclass: `vcc, r1, r2, rc, re, beta, vbe` (floats, SI units).
  - `BiasResult` frozen dataclass: `vth, rth, ib, ic, ie, vb, ve, vc, vce` (floats), `region: Region`, `warnings: tuple[str, ...]`.
  - `ValidationError(Exception)` with attribute `errors: list[str]`.
  - `FIELD_NAMES: tuple[str, ...] = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")`.
  - `DEFAULTS: dict[str, str] = {"vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1", "beta": "100", "vbe": "0.70"}`.
  - `parse_form(raw: Mapping[str, str]) -> BiasInputs` — kΩ→Ω for `r1, r2, rc, re`; raises `ValidationError`.
  - `calculate(vcc, r1, r2, rc, re, beta, vbe) -> BiasResult` — SI only.
  - `VCE_SAT: float = 0.3`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_dc_bias.py`:

```python
import math
import unittest

import dc_bias
from dc_bias import BiasInputs, Region


def si(r1_k=100, r2_k=22, rc_k=2.2, re_k=1):
    """Same helper the web form implies: kΩ in, Ω out."""
    return dict(r1=r1_k * 1000, r2=r2_k * 1000, rc=rc_k * 1000, re=re_k * 1000)


class ReferenceCaseTest(unittest.TestCase):
    def test_reference_case_matches_hand_calculation(self):
        p = si()
        result = dc_bias.calculate(12.0, p["r1"], p["r2"], p["rc"], p["re"], 100.0, 0.70)
        self.assertAlmostEqual(result.vth, 2.164, delta=0.001)
        self.assertAlmostEqual(result.rth, 18032.8, delta=0.1)
        self.assertAlmostEqual(result.ib, 12.299e-6, delta=1e-8)
        self.assertAlmostEqual(result.ic, 1.2299e-3, delta=1e-7)
        self.assertAlmostEqual(result.ie, 1.2422e-3, delta=1e-7)
        self.assertAlmostEqual(result.ve, 1.242, delta=0.01)
        self.assertAlmostEqual(result.vb, 1.942, delta=0.01)
        self.assertAlmostEqual(result.vc, 9.294, delta=0.01)
        self.assertAlmostEqual(result.vce, 8.052, delta=0.01)
        self.assertEqual(result.region, Region.ACTIVE)
        self.assertEqual(result.warnings, ())


class UnitConversionTest(unittest.TestCase):
    def test_parse_form_converts_kilo_ohms(self):
        inputs = dc_bias.parse_form(dc_bias.DEFAULTS)
        self.assertIsInstance(inputs, BiasInputs)
        self.assertAlmostEqual(inputs.r1, 100000.0)
        self.assertAlmostEqual(inputs.r2, 22000.0)
        self.assertAlmostEqual(inputs.rc, 2200.0)
        self.assertAlmostEqual(inputs.re, 1000.0)

    def test_kilo_form_and_ohm_form_agree(self):
        by_kilo = dc_bias.parse_form(dc_bias.DEFAULTS)
        by_ohm = BiasInputs(12.0, 100000.0, 22000.0, 2200.0, 1000.0, 100.0, 0.70)
        self.assertEqual(by_kilo, by_ohm)
        a = dc_bias.calculate(
            by_kilo.vcc, by_kilo.r1, by_kilo.r2, by_kilo.rc, by_kilo.re, by_kilo.beta, by_kilo.vbe
        )
        b = dc_bias.calculate(
            by_ohm.vcc, by_ohm.r1, by_ohm.r2, by_ohm.rc, by_ohm.re, by_ohm.beta, by_ohm.vbe
        )
        self.assertEqual(a, b)


class RegionTest(unittest.TestCase):
    def test_cutoff_when_vth_below_vbe(self):
        p = si(r2_k=1)
        result = dc_bias.calculate(12.0, p["r1"], p["r2"], p["rc"], p["re"], 100.0, 0.70)
        self.assertEqual(result.region, Region.CUTOFF)
        self.assertEqual(result.ic, 0.0)
        self.assertEqual(result.ie, 0.0)
        self.assertTrue(result.warnings)

    def test_near_saturation_boundary(self):
        # RC = 8.5 kΩ -> VCE ≈ 0.304 V (active); RC = 8.6 kΩ -> VCE ≈ 0.181 V (saturated)
        p = si(rc_k=8.5)
        active = dc_bias.calculate(12.0, p["r1"], p["r2"], p["rc"], p["re"], 100.0, 0.70)
        self.assertEqual(active.region, Region.ACTIVE)

        p = si(rc_k=8.6)
        saturated = dc_bias.calculate(12.0, p["r1"], p["r2"], p["rc"], p["re"], 100.0, 0.70)
        self.assertEqual(saturated.region, Region.SATURATION)
        self.assertTrue(saturated.warnings)

    def test_vth_just_above_vbe_is_active(self):
        # R2 = 7 kΩ -> VTH = 0.785 V. VBE 0.78 V barely conducts; 0.79 V cuts off.
        p = si(r2_k=7)
        active = dc_bias.calculate(12.0, p["r1"], p["r2"], p["rc"], p["re"], 100.0, 0.78)
        self.assertEqual(active.region, Region.ACTIVE)
        self.assertGreater(active.ic, 0.0)
        cutoff = dc_bias.calculate(12.0, p["r1"], p["r2"], p["rc"], p["re"], 100.0, 0.79)
        self.assertEqual(cutoff.region, Region.CUTOFF)


class ValidationTest(unittest.TestCase):
    def assert_rejected(self, field, raw_value):
        raw = dict(dc_bias.DEFAULTS)
        raw[field] = raw_value
        with self.assertRaises(dc_bias.ValidationError) as ctx:
            dc_bias.parse_form(raw)
        self.assertTrue(any(field.upper() in message for message in ctx.exception.errors))

    def test_zero_resistor_rejected(self):
        self.assert_rejected("r1", "0")

    def test_beta_below_one_rejected(self):
        self.assert_rejected("beta", "0.5")

    def test_vbe_above_vcc_rejected(self):
        self.assert_rejected("vbe", "12")

    def test_non_numeric_rejected(self):
        self.assert_rejected("rc", "abc")

    def test_comma_decimal_rejected(self):
        self.assert_rejected("rc", "1,5")

    def test_scientific_notation_and_whitespace_accepted(self):
        raw = dict(dc_bias.DEFAULTS)
        raw["r1"] = " 1e2 "
        raw["rc"] = " 2.2E0 "
        inputs = dc_bias.parse_form(raw)
        self.assertEqual(inputs.r1, 100000.0)
        self.assertEqual(inputs.rc, 2200.0)

    def test_missing_field_rejected(self):
        raw = dict(dc_bias.DEFAULTS)
        raw.pop("vbe")
        with self.assertRaises(dc_bias.ValidationError) as ctx:
            dc_bias.parse_form(raw)
        self.assertTrue(any("VBE" in message for message in ctx.exception.errors))

    def test_minimum_beta_computes(self):
        raw = dict(dc_bias.DEFAULTS)
        raw["beta"] = "1"
        inputs = dc_bias.parse_form(raw)
        result = dc_bias.calculate(
            inputs.vcc, inputs.r1, inputs.r2, inputs.rc, inputs.re, inputs.beta, inputs.vbe
        )
        self.assertTrue(math.isfinite(result.ic))
        self.assertGreater(result.ic, 0.0)
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m unittest discover -s tests -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dc_bias'`.

- [ ] **Step 3: Implement `dc_bias.py`**

Use these exact semantics:

- Parsing helper `_to_float(field, raw)`: strip whitespace; reject empty; `float()`; on `ValueError` raise `ValidationError([f"{field.upper()} must be a number"])`. Do **not** strip commas (so `1,5` fails naturally).
- Resistor fields multiply by `1000.0` after parsing.
- Validation rules, each producing one message that contains the field name in upper case:
  - `VCC must be greater than 0`
  - `R1 must be greater than 0 (kΩ)` and the same for `R2`, `RC`, `RE`
  - `BETA must be at least 1`
  - `VBE must be greater than 0 and less than VCC`
- Collect all messages, then raise `ValidationError(errors)` once with the full list.
- `calculate` body:
  ```python
  vth = vcc * r2 / (r1 + r2)
  rth = r1 * r2 / (r1 + r2)
  if vth <= vbe:                      # cutoff
      ib = ic = ie = ve = 0.0
      vb = vth
      vc = vcc
  else:
      ib = (vth - vbe) / (rth + (beta + 1.0) * re)
      ic = beta * ib
      ie = (beta + 1.0) * ib
      ve = ie * re
      vb = ve + vbe
      vc = vcc - ic * rc
  vce = vc - ve
  ```
- Region and warnings:
  - `vth <= vbe` → `CUTOFF`, warning `"Cutoff: VTH <= VBE, the base-emitter junction is not forward biased. Transistor is OFF."`
  - else `vce <= VCE_SAT` → `SATURATION`, warning `"Saturation: VCE <= 0.3 V. The forward-active approximation is not valid; these numbers must not be treated as accurate."`
  - else if all values finite → `ACTIVE`, no warnings
  - else → `INVALID`, warning `"Result is not finite; check the input values."`
- Build `requirements.txt`:
  ```
  Flask>=3.0,<4.0
  ```
- Build `.gitignore`:
  ```
  .venv/
  __pycache__/
  *.pyc
  .env
  .pytest_cache/
  ```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python -m unittest discover -s tests -v`
Expected: `Ran 14 tests` … `OK`.

- [ ] **Step 5: Create the local virtual environment (not committed)**

Run:
```
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```
Expected: Flask installs without error.

- [ ] **Step 6: Hand off to the student for Commit 1**

Tell the student exactly this (do not run git):

- Open GitHub Desktop → repo `BJT DC Bias Web App`
- Tick: `.gitignore`, `requirements.txt`, `dc_bias.py`, `tests/__init__.py`, `tests/test_dc_bias.py`, `docs/`
- Summary: `Add DC bias engineering module with validation and unit tests`
- Click **Commit to main** (then **Push origin** if a remote exists)

Wait for the student to confirm, then verify with `git log --oneline -1` and `git status --short`.

---

### Task 2: Flask routes, template, styling, and web tests

**Files:**
- Create: `app.py`
- Create: `templates/index.html`
- Create: `static/style.css`
- Create: `tests/test_web.py`

**Interfaces:**
- Consumes: `dc_bias.DEFAULTS`, `dc_bias.FIELD_NAMES`, `dc_bias.parse_form`, `dc_bias.calculate`, `dc_bias.ValidationError`, `BiasResult`, `Region`.
- Produces:
  - `create_app() -> Flask`
  - module-level `app = create_app()`
  - routes `GET /` and `POST /calculate`
  - template context keys: `form` (dict of raw strings), `errors` (list[str]), `result` (BiasResult | None), `defaults` (dict).

- [ ] **Step 1: Write the failing web tests**

Create `tests/test_web.py`:

```python
import unittest

from app import create_app

REFERENCE = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "beta": "100",
    "vbe": "0.70",
}


class WebTest(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_get_index_returns_form(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        for field in REFERENCE:
            self.assertIn(f'name="{field}"', body)

    def test_post_reference_case_renders_results(self):
        response = self.client.post("/calculate", data=REFERENCE)
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("1.942", body)
        self.assertIn("9.294", body)
        self.assertIn("1.230", body)
        self.assertIn("Active", body)

    def test_post_invalid_input_shows_error_without_results(self):
        bad = dict(REFERENCE, r1="0")
        response = self.client.post("/calculate", data=bad)
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("R1", body)
        self.assertNotIn("8.052", body)
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`.

- [ ] **Step 3: Implement `app.py`**

```python
from flask import Flask, render_template, request

import dc_bias


def create_app():
    app = Flask(__name__)

    def render_index(form, errors, result):
        return render_template(
            "index.html",
            form=form,
            errors=errors,
            result=result,
            defaults=dc_bias.DEFAULTS,
        )

    @app.get("/")
    def index():
        return render_index(dict(dc_bias.DEFAULTS), [], None)

    @app.post("/calculate")
    def calculate_bias():
        raw = {name: request.form.get(name, "") for name in dc_bias.FIELD_NAMES}
        try:
            inputs = dc_bias.parse_form(raw)
        except dc_bias.ValidationError as exc:
            return render_index(raw, exc.errors, None)
        result = dc_bias.calculate(
            inputs.vcc, inputs.r1, inputs.r2, inputs.rc, inputs.re, inputs.beta, inputs.vbe
        )
        return render_index(raw, [], result)

    return app


app = create_app()
```

- [ ] **Step 4: Implement `templates/index.html`**

Requirements the tests depend on:
- Seven inputs with `name="vcc"`, `name="r1"`, `name="r2"`, `name="rc"`, `name="re"`, `name="beta"`, `name="vbe"`, each with `value="{{ form.vcc }}"` style stickiness and unit hints `V`, `kΩ`, `kΩ`, `kΩ`, `kΩ`, `—`, `V`.
- Form posts to `{{ url_for('calculate_bias') }}` with `method="post"`.
- When `errors` is non-empty: render `<ul class="error">` with one `<li>` per message and **no results table**.
- When `result` is present: render a values table with `VTH`, `RTH`, `VB`, `VE`, `VC`, `VCE`, `IB`, `IC`, `IE` formatted `{{ '%.3f'|format(result.vb) }}` etc., converting `ib`/`ic`/`ie` to µA/mA/mA in the template **for display only** (`result.ib * 1e6`, `result.ic * 1e3`, `result.ie * 1e3`).
- Region label text: `Active`, `Cutoff`, `Saturation`, `Invalid` (title case). The word `Active` must appear verbatim for the valid case.
- When `result.warnings` is non-empty: render `<ul class="warning">` with each message.
- Include `<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">` and a footer noting the forward-active approximation.

- [ ] **Step 5: Implement `static/style.css`**

Single responsive stylesheet: max-width 900 px centered, system font stack, form as a two-column grid collapsing to one column under 640 px, table with header row, distinct `.error` (red) and `.warning` (amber) blocks. No external fonts or frameworks.

- [ ] **Step 6: Run the tests and confirm they pass**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: `Ran 17 tests` … `OK`.

- [ ] **Step 7: Manual browser check**

Run: `.\.venv\Scripts\python.exe -m flask --app app run --debug`
Open `http://127.0.0.1:5000/`, submit the defaults, confirm VB 1.942 V / VC 9.294 V / IC 1.230 mA / Region Active. Then submit `R1 = 0` and confirm the error panel and no results. Stop the server.

- [ ] **Step 8: Hand off to the student for Commit 2**

- Tick: `app.py`, `templates/index.html`, `static/style.css`, `tests/test_web.py`
- Summary: `Add Flask routes, template and HTTP tests`
- Click **Commit to main**, then **Push origin**

Wait for confirmation, then verify with `git log --oneline -2` and `git status --short`.

---

### Task 3: Documentation and reproducibility proof

**Files:**
- Create: `README.md`
- Create: `AGENTS.md`
- Create: `docs/design-note.md`
- Create: `docs/validation.md`
- Create: `docs/reflection.md`

**Interfaces:**
- Consumes: the finished app and the numbers from Task 1's reference test.
- Produces: no code interfaces.

- [ ] **Step 1: Write `docs/validation.md`**

Include the hand calculation for the reference case with the numbers the tests assert:

```
VTH = 12 × 22/(100+22)      = 2.164 V
RTH = 100×22/(100+22) kΩ    = 18.033 kΩ
IB  = (2.164−0.70)/(18033+101×1000) = 12.299 µA
IC  = 100 × 12.299 µA       = 1.230 mA
IE  = 101 × 12.299 µA       = 1.242 mA
VE  = 1.242 mA × 1 kΩ       = 1.242 V
VB  = 1.242 + 0.70          = 1.942 V
VC  = 12 − 1.230 mA×2.2 kΩ  = 9.294 V
VCE = 9.294 − 1.242         = 8.052 V   → ACTIVE
```
Add the two out-of-region cases (cutoff with R2 = 1 kΩ; saturation with RC = 8.6 kΩ) and a tolerance note (±0.01 V / ±0.01 mA).

- [ ] **Step 2: Write `README.md`**

Sections: what it is, requirements (Python 3.10+), install (`python -m venv .venv`, `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`), run (`.\.venv\Scripts\python.exe -m flask --app app run --debug` → `http://127.0.0.1:5000/`), test (`python -m unittest discover -s tests -v`), reference result table, and a **Model limits** section stating the forward-active approximation with constant β and VBE, and that cutoff/saturation results carry warnings. Note explicitly that opening `templates/index.html` directly does not run the calculation.

- [ ] **Step 3: Write `AGENTS.md`**

Rules: engineering math lives only in `dc_bias.py`; never compute in templates; kΩ→Ω conversion only in `parse_form`; every behaviour change needs a test; never commit `.venv/`, `.env` or secrets; commits are made in GitHub Desktop by the student.

- [ ] **Step 4: Write `docs/design-note.md`**

Summarise the chosen approach (A), the rejected alternatives, the file layout and the region thresholds, linking to the spec.

- [ ] **Step 5: Write `docs/reflection.md`**

Answer the four handout questions: (1) why `file://` on `templates/index.html` is not Flask, (2) how the form sends data to Python, (3) whether changing an equation in `dc_bias.py` requires editing HTML, (4) why out-of-region results need warnings.

- [ ] **Step 6: Run the full suite one more time**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: `Ran 17 tests` … `OK`.

- [ ] **Step 7: Prove reproducibility from a fresh clone**

Run (from a temp dir, after the student has committed):
```
git clone "C:\Users\b6821654\Documents\GitHub\BJT DC Bias Web App" fresh-check
cd fresh-check
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
Expected: `Ran 17 tests` … `OK` in the fresh clone.

- [ ] **Step 8: Hand off to the student for Commit 3**

- Tick: `README.md`, `AGENTS.md`, `docs/design-note.md`, `docs/validation.md`, `docs/reflection.md`
- Summary: `Add documentation, validation notes and reflection`
- Click **Commit to main**, then **Push origin**

- [ ] **Step 9: Final acceptance report**

Produce a table mapping A1–A7 to the command output or screenshot that proves each one, and list the commit SHAs from `git log --oneline`.

---

## Notes for the implementer

- Do not create files outside the list for the current task.
- Do not run `git add`, `git commit` or `git push`; the student commits in GitHub Desktop.
- If a verification command fails, stop and report the exact output instead of continuing to the next task.
