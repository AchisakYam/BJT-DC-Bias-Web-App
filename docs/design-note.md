# Design note — BJT DC Bias Web App

Full design: [`superpowers/specs/2026-11-10-bjt-dc-bias-design.md`](superpowers/specs/2026-11-10-bjt-dc-bias-design.md)

## Approach chosen

Two routes and a separate engineering module:

```
GET  /           → render the form
POST /calculate  → parse + validate → calculate → render results or errors
```

`dc_bias.py` owns the equations, the kΩ → Ω conversion and the region logic;
`app.py` owns HTTP; Jinja only formats values for display.

## Alternatives rejected

| Alternative | Why not |
|-------------|---------|
| Single `GET/POST /` route | Shorter, but makes the frontend/backend split less obvious and weakens route-level tests |
| JSON API + `fetch` | Extra JavaScript, JSON contract and client-side error handling for no benefit in a 3-hour lab |

## File responsibilities

```
app.py                  routes, template context
dc_bias.py              BiasInputs, BiasResult, parse_form, calculate, Region
templates/index.html    form, error panel, warning panel, results table
static/style.css        responsive styling, no framework
tests/                  unit tests + HTTP tests
```

## Region thresholds

- `CUTOFF` when `VTH ≤ VBE` — the base-emitter junction is not forward biased.
- `SATURATION` when `VCE ≤ 0.3 V` — the forward-active equations no longer hold.
- `ACTIVE` otherwise.
- `INVALID` for non-finite results (defensive; unreachable after validation).

Cutoff and saturation results are shown together with a warning, because the
computed numbers exist but are not trustworthy in those regions.

## Display decisions

- Resistors entered in kΩ (matches the lab sheet and datasheets).
- Three decimals for V, mA and µA.
- VTH and RTH are shown so the calculation can be followed by hand.
- Errors keep the user's raw input so a typo only needs one field corrected.
