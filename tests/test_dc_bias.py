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

    def test_non_finite_values_rejected(self):
        for field, raw_value in (("r1", "nan"), ("vcc", "inf"), ("r2", "1e999")):
            raw = dict(dc_bias.DEFAULTS)
            raw[field] = raw_value
            with self.assertRaises(dc_bias.ValidationError) as ctx:
                dc_bias.parse_form(raw)
            self.assertTrue(
                any(field.upper() in message for message in ctx.exception.errors),
                f"{field}={raw_value} was not reported: {ctx.exception.errors}",
            )

    def test_minimum_beta_computes(self):
        raw = dict(dc_bias.DEFAULTS)
        raw["beta"] = "1"
        inputs = dc_bias.parse_form(raw)
        result = dc_bias.calculate(
            inputs.vcc, inputs.r1, inputs.r2, inputs.rc, inputs.re, inputs.beta, inputs.vbe
        )
        self.assertTrue(math.isfinite(result.ic))
        self.assertGreater(result.ic, 0.0)
