"""DC bias calculations for three NPN common-emitter bias circuits.

This module is deliberately free of Flask/HTML knowledge. The web layer converts
form text into SI units here and renders the returned ``BiasResult``.

Supported modes:

* ``divider``  - voltage-divider bias (the original Lab 02 circuit, unchanged)
* ``fixed``    - fixed bias with RB from VCC to base
* ``emitter``  - emitter bias with RB and RE, single supply

Model: forward-active approximation with constant beta and constant VBE.
It is not a SPICE solver; results outside the forward-active region are flagged.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

KILO = 1000.0
VCE_SAT = 0.3

FIELD_NAMES: tuple[str, ...] = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")
ALL_FIELD_NAMES: tuple[str, ...] = ("vcc", "r1", "r2", "rb", "rc", "re", "beta", "vbe")

RESISTOR_FIELDS = ("r1", "r2", "rb", "rc", "re")

DEFAULT_MODE = "divider"
MODES: tuple[str, ...] = ("divider", "fixed", "emitter")
MODE_LABELS: dict[str, str] = {
    "divider": "Voltage Divider Bias",
    "fixed": "Fixed Bias",
    "emitter": "Emitter Bias",
}
MODE_FIELDS: dict[str, tuple[str, ...]] = {
    "divider": ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"),
    "fixed": ("vcc", "rb", "rc", "beta", "vbe"),
    "emitter": ("vcc", "rb", "rc", "re", "beta", "vbe"),
}

DEFAULTS: dict[str, str] = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "beta": "100",
    "vbe": "0.70",
}
RB_DEFAULT = "1000"  # kΩ -> 1 MΩ for the fixed and emitter reference cases


class Region(str, Enum):
    ACTIVE = "active"
    CUTOFF = "cutoff"
    SATURATION = "saturation"
    INVALID = "invalid"


class ValidationError(Exception):
    """Raised when form values cannot be used for a calculation."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = list(errors)


@dataclass(frozen=True)
class BiasInputs:
    """Circuit values in SI units (volts and ohms).

    ``rb`` defaults to 0.0 so existing seven-argument callers and divider
    forms keep producing an equal object.
    """

    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float
    rb: float = 0.0


@dataclass(frozen=True)
class BiasResult:
    """DC operating point. All currents in amperes, voltages in volts."""

    vth: float
    rth: float
    ib: float
    ic: float
    ie: float
    vb: float
    ve: float
    vc: float
    vce: float
    region: Region
    warnings: tuple[str, ...]
    mode: str = DEFAULT_MODE

    def to_dict(self) -> dict[str, object]:
        """Return the result with explicit units, as expected by the lab spec."""
        warning = self.warnings[0] if self.warnings else ""
        return {
            "mode": self.mode,
            "mode_label": MODE_LABELS.get(self.mode, self.mode),
            "vth_v": self.vth,
            "rth_kohm": self.rth / KILO,
            "ib_ua": self.ib * 1e6,
            "ic_ma": self.ic * 1e3,
            "ie_ma": self.ie * 1e3,
            "vb_v": self.vb,
            "ve_v": self.ve,
            "vc_v": self.vc,
            "vce_v": self.vce,
            "region": self.region.value,
            "warning": warning,
            "warnings": list(self.warnings),
        }


def is_known_mode(mode: str) -> bool:
    return mode in MODE_FIELDS


def _to_float(field: str, raw: str | None, errors: list[str]) -> float | None:
    text = (raw or "").strip()
    if not text:
        errors.append(f"{field.upper()} is required")
        return None
    try:
        value = float(text)
    except ValueError:
        errors.append(f"{field.upper()} must be a number")
        return None
    if not math.isfinite(value):
        errors.append(f"{field.upper()} must be a finite number")
        return None
    return value


def parse_form(raw: Mapping[str, str], mode: str | None = None) -> BiasInputs:
    """Validate the fields needed by ``mode`` and convert kΩ to Ω.

    With no explicit mode the submitted ``mode`` field is used, falling back
    to ``divider``. Values for fields a mode does not use are ignored and left
    at 0.0 in SI units.

    Raises:
        ValidationError: with every problem found, not just the first one.
    """
    selected = (mode if mode is not None else raw.get("mode", DEFAULT_MODE)) or DEFAULT_MODE
    selected = str(selected).strip().lower()
    if not is_known_mode(selected):
        raise ValidationError([f"Unknown circuit mode: {selected}"])

    needed = MODE_FIELDS[selected]
    errors: list[str] = []
    values: dict[str, float | None] = {name: 0.0 for name in ALL_FIELD_NAMES}
    for name in needed:
        values[name] = _to_float(name, raw.get(name), errors)

    if values["vcc"] is not None and values["vcc"] <= 0:
        errors.append("VCC must be greater than 0")

    for name in RESISTOR_FIELDS:
        if name not in needed:
            continue
        value = values[name]
        if value is not None and value <= 0:
            errors.append(f"{name.upper()} must be greater than 0 (kΩ)")

    beta = values["beta"]
    if beta is not None and beta < 1:
        errors.append("BETA must be at least 1")

    vcc = values["vcc"]
    vbe = values["vbe"]
    if vbe is not None and vcc is not None and not (0 < vbe < vcc):
        errors.append("VBE must be greater than 0 and less than VCC")

    if errors:
        raise ValidationError(errors)

    return BiasInputs(
        vcc=float(values["vcc"]),
        r1=float(values["r1"]) * KILO,
        r2=float(values["r2"]) * KILO,
        rc=float(values["rc"]) * KILO,
        re=float(values["re"]) * KILO,
        beta=float(values["beta"]),
        vbe=float(values["vbe"]),
        rb=float(values["rb"]) * KILO,
    )


def _classify_simple(ib: float, vce: float, finite: bool) -> tuple[Region, tuple[str, ...]]:
    """Region and warning for fixed / emitter bias."""
    if ib <= 0:
        return Region.CUTOFF, (
            "Cutoff: base current is not positive. The forward-active model may not apply.",
        )
    if vce <= VCE_SAT:
        return Region.SATURATION, (
            "Saturation: VCE <= 0.3 V. The forward-active model may not apply; "
            "these numbers must not be treated as accurate.",
        )
    if not finite:
        return Region.INVALID, ("Result is not finite; check the input values.",)
    return Region.ACTIVE, ()


def calculate(vcc, r1, r2, rc, re, beta, vbe) -> BiasResult:
    """Compute the voltage-divider bias point from SI values.

    ``r1, r2, rc, re`` are ohms; ``vcc, vbe`` are volts; ``beta`` is dimensionless.
    This is the original Lab 02 calculation and its behaviour is unchanged.
    """
    vth = vcc * r2 / (r1 + r2)
    rth = r1 * r2 / (r1 + r2)

    if vth <= vbe:
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

    if vth <= vbe:
        region = Region.CUTOFF
        warnings = (
            "Cutoff: VTH <= VBE, the base-emitter junction is not forward biased. "
            "Transistor is OFF.",
        )
    elif vce <= VCE_SAT:
        region = Region.SATURATION
        warnings = (
            "Saturation: VCE <= 0.3 V. The forward-active approximation is not valid; "
            "these numbers must not be treated as accurate.",
        )
    elif all(math.isfinite(value) for value in (vth, rth, ib, ic, ie, vb, ve, vc, vce)):
        region = Region.ACTIVE
        warnings = ()
    else:
        region = Region.INVALID
        warnings = ("Result is not finite; check the input values.",)

    return BiasResult(
        vth=vth,
        rth=rth,
        ib=ib,
        ic=ic,
        ie=ie,
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vce,
        region=region,
        warnings=warnings,
        mode="divider",
    )


def calculate_fixed(vcc, rb, rc, beta, vbe) -> BiasResult:
    """Fixed bias: IB = (VCC - VBE) / RB, emitter tied to ground."""
    ib = (vcc - vbe) / rb
    ic = beta * ib
    ie = (beta + 1.0) * ib
    ve = 0.0
    vb = vbe
    vc = vcc - ic * rc
    vce = vc - ve

    finite = all(math.isfinite(value) for value in (ib, ic, ie, vb, ve, vc, vce))
    region, warnings = _classify_simple(ib, vce, finite)

    return BiasResult(
        vth=0.0,
        rth=0.0,
        ib=ib,
        ic=ic,
        ie=ie,
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vce,
        region=region,
        warnings=warnings,
        mode="fixed",
    )


def calculate_emitter(vcc, rb, rc, re, beta, vbe) -> BiasResult:
    """Emitter bias: IB = (VCC - VBE) / [RB + (beta + 1) RE]."""
    ib = (vcc - vbe) / (rb + (beta + 1.0) * re)
    ic = beta * ib
    ie = (beta + 1.0) * ib
    ve = ie * re
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve

    finite = all(math.isfinite(value) for value in (ib, ic, ie, vb, ve, vc, vce))
    region, warnings = _classify_simple(ib, vce, finite)

    return BiasResult(
        vth=0.0,
        rth=0.0,
        ib=ib,
        ic=ic,
        ie=ie,
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vce,
        region=region,
        warnings=warnings,
        mode="emitter",
    )


def calculate_for_mode(mode: str, inputs: BiasInputs) -> BiasResult:
    """Dispatch to the calculation belonging to ``mode``."""
    selected = str(mode).strip().lower()
    if selected == "divider":
        return calculate(
            inputs.vcc, inputs.r1, inputs.r2, inputs.rc, inputs.re, inputs.beta, inputs.vbe
        )
    if selected == "fixed":
        return calculate_fixed(inputs.vcc, inputs.rb, inputs.rc, inputs.beta, inputs.vbe)
    if selected == "emitter":
        return calculate_emitter(inputs.vcc, inputs.rb, inputs.rc, inputs.re, inputs.beta, inputs.vbe)
    raise ValidationError([f"Unknown circuit mode: {selected}"])
