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

    def test_post_cutoff_shows_warning(self):
        body = self.client.post("/calculate", data=dict(REFERENCE, r2="1")).get_data(as_text=True)
        self.assertIn("Cutoff", body)
        self.assertIn('class="warning"', body)

    def test_post_saturation_shows_warning(self):
        body = self.client.post("/calculate", data=dict(REFERENCE, rc="8.6")).get_data(as_text=True)
        self.assertIn("Saturation", body)
        self.assertIn('class="warning"', body)

    def test_post_non_finite_value_shows_error(self):
        response = self.client.post("/calculate", data=dict(REFERENCE, r1="nan"))
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("R1 must be a finite number", body)
        self.assertNotIn("8.052", body)
