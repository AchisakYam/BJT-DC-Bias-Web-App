"""Lab 03 acceptance: three bias modes selected from the web form."""

import unittest

import dc_bias
from app import create_app
from dc_bias import Region

LAB = {"vcc": "12", "rc": "2.2", "beta": "100", "vbe": "0.70", "rb": "1000"}


class NewModeCalculationTest(unittest.TestCase):
    def test_fixed_bias_reference_case(self):
        result = dc_bias.calculate_fixed(12.0, 1_000_000.0, 2200.0, 100.0, 0.70)
        self.assertAlmostEqual(result.ib * 1e6, 11.300, places=3)
        self.assertAlmostEqual(result.ic * 1e3, 1.130, places=3)
        self.assertAlmostEqual(result.ve, 0.0, places=3)
        self.assertAlmostEqual(result.vb, 0.700, places=3)
        self.assertAlmostEqual(result.vc, 9.514, places=3)
        self.assertAlmostEqual(result.vce, 9.514, places=3)
        self.assertEqual(result.region, Region.ACTIVE)

    def test_emitter_bias_reference_case(self):
        result = dc_bias.calculate_emitter(12.0, 1_000_000.0, 2200.0, 1000.0, 100.0, 0.70)
        self.assertAlmostEqual(result.ic * 1e3, 1.026, places=2)
        self.assertAlmostEqual(result.ve, 1.037, places=2)
        self.assertAlmostEqual(result.vce, 8.705, places=2)
        self.assertEqual(result.region, Region.ACTIVE)

    def test_emitter_re_doubling_reduces_ic(self):
        a = dc_bias.calculate_emitter(12.0, 1_000_000.0, 2200.0, 1000.0, 100.0, 0.70)
        b = dc_bias.calculate_emitter(12.0, 1_000_000.0, 2200.0, 2000.0, 100.0, 0.70)
        self.assertLess(b.ic, a.ic)

    def test_result_exposes_named_units(self):
        result = dc_bias.calculate_fixed(12.0, 1_000_000.0, 2200.0, 100.0, 0.70)
        data = result.to_dict()
        for key in ("vb_v", "ve_v", "vc_v", "vce_v", "ic_ma", "warning"):
            self.assertIn(key, data)
        self.assertAlmostEqual(data["ic_ma"], 1.130, places=3)

    def test_divider_result_is_unchanged(self):
        p = dc_bias.parse_form(dc_bias.DEFAULTS)
        result = dc_bias.calculate_for_mode("divider", p)
        self.assertAlmostEqual(result.ic * 1e3, 1.230, places=2)
        self.assertAlmostEqual(result.vce, 8.052, places=2)


class ModeValidationTest(unittest.TestCase):
    def test_fixed_mode_does_not_require_divider_fields(self):
        inputs = dc_bias.parse_form(LAB, mode="fixed")
        self.assertAlmostEqual(inputs.rb, 1_000_000.0)
        result = dc_bias.calculate_for_mode("fixed", inputs)
        self.assertEqual(result.mode, "fixed")

    def test_fixed_mode_rejects_zero_rb(self):
        raw = dict(LAB, rb="0")
        with self.assertRaises(dc_bias.ValidationError) as ctx:
            dc_bias.parse_form(raw, mode="fixed")
        self.assertTrue(any("RB" in message for message in ctx.exception.errors))

    def test_emitter_mode_requires_re(self):
        raw = dict(LAB)
        raw["re"] = ""
        with self.assertRaises(dc_bias.ValidationError) as ctx:
            dc_bias.parse_form(raw, mode="emitter")
        self.assertTrue(any("RE" in message for message in ctx.exception.errors))

    def test_unknown_mode_is_an_error(self):
        with self.assertRaises(dc_bias.ValidationError) as ctx:
            dc_bias.parse_form(LAB, mode="magic")
        self.assertTrue(any("mode" in message.lower() for message in ctx.exception.errors))


class Lab03WebTest(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_get_offers_three_modes(self):
        body = self.client.get("/").get_data(as_text=True)
        for mode in ("divider", "fixed", "emitter"):
            self.assertIn(f'value="{mode}"', body)

    def test_fixed_post_shows_mode_and_result(self):
        data = dict(LAB, mode="fixed")
        body = self.client.post("/calculate", data=data).get_data(as_text=True)
        self.assertIn("Fixed Bias", body)
        self.assertIn("1.130", body)
        self.assertIn("9.514", body)

    def test_emitter_post_shows_mode_and_result(self):
        data = dict(LAB, re="1", mode="emitter")
        body = self.client.post("/calculate", data=data).get_data(as_text=True)
        self.assertIn("Emitter Bias", body)
        self.assertIn("1.026", body)
        self.assertIn("8.705", body)

    def test_invalid_fixed_post_has_error_and_no_stale_result(self):
        data = dict(LAB, mode="fixed", rb="0")
        body = self.client.post("/calculate", data=data).get_data(as_text=True)
        self.assertIn("RB", body)
        self.assertNotIn("DC operating point", body)
        self.assertNotIn("1.130", body)

    def test_unknown_mode_post_shows_error(self):
        data = dict(LAB, mode="magic")
        body = self.client.post("/calculate", data=data).get_data(as_text=True)
        self.assertIn("mode", body.lower())
        self.assertNotIn("DC operating point", body)


if __name__ == "__main__":
    unittest.main()
