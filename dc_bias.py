"""DC bias calculations for an NPN common-emitter voltage-divider circuit.

This module is deliberately free of Flask/HTML knowledge. The web layer converts
form text into SI units here and renders the returned ``BiasResult``.

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

RESISTOR_FIELDS = ("r1", "r2", "rc", "re")

DEFAULTS: dict[str, str] = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "beta": "100",
    "vbe": "0.70",
}


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
    """Circuit values in SI units (volts and ohms)."""

    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float


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


def parse_form(raw: Mapping[str, str]) -> BiasInputs:
    """Validate raw form text and convert kΩ to Ω.

    Raises:
        ValidationError: with every problem found, not just the first one.
    """
    errors: list[str] = []
    values: dict[str, float | None] = {
        field: _to_float(field, raw.get(field), errors) for field in FIELD_NAMES
    }

    if values["vcc"] is not None and values["vcc"] <= 0:
        errors.append("VCC must be greater than 0")

    for name in RESISTOR_FIELDS:
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
    )


def calculate(vcc, r1, r2, rc, re, beta, vbe) -> BiasResult:
    """Compute the DC operating point from SI values.

    ``r1, r2, rc, re`` are ohms; ``vcc, vbe`` are volts; ``beta`` is dimensionless.
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
    )
