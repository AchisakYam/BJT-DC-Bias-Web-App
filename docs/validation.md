# Validation — BJT DC Bias Web App

All numbers below were computed independently by hand, then compared with the app
and with the automated tests in `tests/`. Model: forward-active approximation,
constant β = 100 and constant VBE = 0.70 V unless stated.

## 1. Reference case (the acceptance case)

Inputs: VCC = 12 V, R1 = 100 kΩ, R2 = 22 kΩ, RC = 2.2 kΩ, RE = 1 kΩ, β = 100, VBE = 0.70 V.

```
VTH = 12 × 22/(100+22)                 = 2.164 V
RTH = 100×22/(100+22) kΩ               = 18.033 kΩ
IB  = (2.164 − 0.70)/(18033 + 101×1000) = 12.299 µA
IC  = 100 × 12.299 µA                  = 1.230 mA
IE  = 101 × 12.299 µA                  = 1.242 mA
VE  = 1.242 mA × 1 kΩ                  = 1.242 V
VB  = 1.242 + 0.70                     = 1.942 V
VC  = 12 − 1.230 mA × 2.2 kΩ           = 9.294 V
VCE = 9.294 − 1.242                    = 8.052 V   → ACTIVE
```

App output (rendered page): VB 1.942 V, VE 1.242 V, VC 9.294 V, VCE 8.052 V,
IC 1.230 mA, IB 12.299 µA, IE 1.242 mA, region **Active**.

Tolerance used in the tests: ±0.01 V for voltages and ±0.01 mA for currents
(the tighter assertions for VTH, RTH, IB, IC, IE are listed in
`tests/test_dc_bias.py`).

## 2. Cutoff case

Same circuit with R2 = 1 kΩ.

```
VTH = 12 × 1/(100+1) = 0.119 V
VTH (0.119 V) ≤ VBE (0.70 V)  →  base-emitter not forward biased
IB = IC = IE = 0, VE = 0, VB = VTH = 0.119 V, VC = VCC = 12 V
Region: CUTOFF, with warning
```

The app reports the region as **Cutoff**, shows zero currents, and displays the
warning that the transistor is off. The forward-active formulas are not used.

## 3. Saturation case

Same circuit with RC = 8.6 kΩ.

```
IB  = 12.299 µA, IC = 1.230 mA, IE = 1.242 mA, VE = 1.242 V
VC  = 12 − 1.230 mA × 8.6 kΩ = 1.423 V
VCE = 1.423 − 1.242 = 0.181 V  →  VCE ≤ 0.3 V
Region: SATURATION, with warning
```

The numbers are still printed, but they come from equations that assume forward
active operation. The app labels them unreliable instead of presenting them as a
verified operating point.

For comparison, RC = 8.5 kΩ gives VCE = 0.304 V, which is just above the 0.3 V
threshold and is therefore reported as **Active**. Both sides of the boundary are
covered by `test_near_saturation_boundary`.

## 4. Validation cases

| Input | Expected behaviour |
|-------|--------------------|
| `R1 = 0` | error naming `R1`, no results |
| `β = 0.5` | error naming `BETA` (β must be at least 1) |
| `VBE = 12` with `VCC = 12` | error naming `VBE` (must be less than VCC) |
| `RC = abc` | error naming `RC` (must be a number) |
| `RC = 1,5` | error naming `RC` (comma is not a decimal separator here) |
| empty / missing field | error naming that field |
| ` 1e2 ` in `R1` | accepted as 100 kΩ |

## 5. Unit check

The form accepts kΩ for R1, R2, RC, RE. `dc_bias.parse_form` performs the single
kΩ → Ω conversion; `dc_bias.calculate` receives ohms only. The test
`test_kilo_form_and_ohm_form_agree` proves both routes give an identical
`BiasResult`.
