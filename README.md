# BJT DC Bias Web App

Lab 03 deliverable for **ENG29 2121 Computer Programming for Electrical Engineers**.
A small Flask web application that computes the DC operating point of an NPN
common-emitter amplifier in three bias circuits: **Voltage Divider**, **Fixed** and
**Emitter** bias. The original voltage-divider results are unchanged.

The browser sends the component values to Python; Python does the calculation; the
result is rendered back into the page. Nothing is calculated in HTML or JavaScript.

## Requirements

- Python 3.10 or newer (developed on Python 3.15)
- Flask 3.x (installed from `requirements.txt`)
- Git, and a browser

## Install

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Linux / macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Run

Windows:

```powershell
.\.venv\Scripts\python.exe -m flask --app app run --debug
```

Linux / macOS:

```bash
.venv/bin/python -m flask --app app run --debug
```

Open <http://127.0.0.1:5000/>. The development server is for local use only; do not
expose it to a network.

## Use

Pick the bias circuit, fill in the fields shown for it, then press **Calculate DC
Bias**. All resistor inputs are in **kΩ**; VCC and VBE are in volts. Only the fields
used by the selected mode are validated.

| Mode | Inputs | Equations (`dc_bias.py`) |
|------|--------|--------------------------|
| Voltage Divider Bias | VCC, R1, R2, RC, RE, β, VBE | `calculate` (unchanged Lab 02) |
| Fixed Bias | VCC, RB, RC, β, VBE | `calculate_fixed` |
| Emitter Bias | VCC, RB, RC, RE, β, VBE | `calculate_emitter` |

Defaults reproduce the Lab 02 reference case:

| Quantity | Value | Unit |
|----------|-------|------|
| VTH | 2.164 | V |
| RTH | 18.033 | kΩ |
| VB | 1.942 | V |
| VE | 1.242 | V |
| VC | 9.294 | V |
| VCE | 8.052 | V |
| IB | 12.299 | µA |
| IC | 1.230 | mA |
| IE | 1.242 | mA |
| Region | Active | — |

With VCC = 12 V, RC = 2.2 kΩ, β = 100 and VBE = 0.70 V:

| Mode | Extra inputs | IC | VCE |
|------|--------------|----|-----|
| Fixed | RB = 1000 kΩ | 1.130 mA | 9.514 V |
| Emitter | RB = 1000 kΩ, RE = 1 kΩ | 1.026 mA | 8.705 V |
| Emitter | RB = 1000 kΩ, RE = 2 kΩ | 0.940 mA | 8.033 V |

`BiasResult.to_dict()` also exposes the values with explicit keys and units
(`vb_v`, `ve_v`, `vc_v`, `vce_v`, `ic_ma`, `warning`, …).

Invalid values produce a readable error message naming the field and the selected
mode; no stale result is shown. Values outside the forward-active region produce a
warning. See `docs/validation.md` for the A1–A5 browser acceptance table.

## Test

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: `Ran 35 tests` … `OK`. This covers the engineering module (reference case,
unit conversion, cutoff, saturation, validation, the two new modes and mode
dispatch) and the HTTP routes through the Flask test client.

## Project layout

```
app.py                  Flask app factory and routes (GET /, POST /calculate)
dc_bias.py              Parsing, validation, three equation sets, mode dispatch
templates/index.html    Mode picker, form + results (Jinja)
static/style.css        Responsive layout, mode-dependent field visibility
tests/test_dc_bias.py   Lab 02 engineering unit tests
tests/test_web.py       Lab 02 Flask test-client tests
tests/test_lab03.py     New-mode calculations, validation and web tests
docs/                   Design note, validation notes (A1–A5), reflection
```

## Model limits

- Forward-active approximation only: constant β, constant VBE, no Early effect.
- Cutoff and saturation are detected per mode: `VTH ≤ VBE` for divider, `IB ≤ 0`
  for fixed/emitter, and `VCE ≤ 0.3 V` for all three. They are reported with a
  warning and must not be read as verified operating points.
- All resistors are ideal; temperature, tolerance and leakage are ignored.
- This is not SPICE and does not solve a full circuit.

## Important

Opening `templates/index.html` directly from disk (`file://`) does **not** run the
application. The page is a Jinja template: the numbers come from the Python backend
through Flask. Always start the server and use `http://127.0.0.1:5000/`.
