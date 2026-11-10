# BJT DC Bias Web App

Lab 02 deliverable for **ENG29 2121 Computer Programming for Electrical Engineers**.
A small Flask web application that computes the DC operating point of an NPN
common-emitter amplifier with voltage-divider bias.

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

Enter VCC (V), R1, R2, RC, RE (kΩ), β and VBE (V), then press **Calculate DC Bias**.
Defaults reproduce the lab reference case:

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

Invalid values produce a readable error message naming the field, and no result is
shown. Values outside the forward-active region produce a warning.

## Test

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: `Ran 21 tests` … `OK`. This covers the engineering module (reference case,
unit conversion, cutoff, saturation, validation) and the HTTP routes through the
Flask test client.

## Project layout

```
app.py                  Flask app factory and routes (GET /, POST /calculate)
dc_bias.py              Parsing, validation, equations, region classification
templates/index.html    Form + results (Jinja)
static/style.css        Responsive layout
tests/test_dc_bias.py   Engineering unit tests
tests/test_web.py       Flask test-client tests
docs/                   Design note, validation notes, reflection
```

## Model limits

- Forward-active approximation only: constant β, constant VBE, no Early effect.
- Cutoff (`VTH ≤ VBE`) and saturation (`VCE ≤ 0.3 V`) are detected, reported with a
  warning, and must not be read as verified operating points.
- All resistors are ideal; temperature, tolerance and leakage are ignored.
- This is not SPICE and does not solve a full circuit.

## Important

Opening `templates/index.html` directly from disk (`file://`) does **not** run the
application. The page is a Jinja template: the numbers come from the Python backend
through Flask. Always start the server and use `http://127.0.0.1:5000/`.
