import unittest
from pathlib import Path
from unittest.mock import patch

from orca.workflow import DataError, investigate, load_csv, parse_csv

SAMPLE = load_csv(Path(__file__).resolve().parents[1] / "data" / "sample.csv")


class WorkflowTests(unittest.TestCase):
    def test_missing_observations_are_not_confirmed_bleaching(self):
        result = investigate(SAMPLE, "Example Reef A", "2026-06-01", "2026-07-15", "Is bleaching proven?")
        self.assertEqual(result["risk"], "high")
        self.assertFalse(any("bleaching was recorded" in c.lower() for c in result["claims"]))
        self.assertTrue(any("No direct bleaching" in x for x in result["limitations"]))

    def test_positive_observation_is_supported(self):
        result = investigate(SAMPLE, "Example Reef C", "2026-06-01", "2026-07-01", "What happened?")
        self.assertEqual(result["risk"], "moderate")
        self.assertTrue(any("Bleaching was recorded" in c for c in result["claims"]))

    def test_out_of_range_abstains(self):
        result = investigate(SAMPLE, "Example Reef A", "2025-01-01", "2025-01-31", "What happened?")
        self.assertEqual(result["risk"], "unknown")
        self.assertFalse(result["evidence"])

    def test_invalid_csv_rejected(self):
        with self.assertRaises(DataError):
            parse_csv(b"site,date\nreef,2026-01-01\n")

    def test_no_dhw_abstains(self):
        csv_data = ("site,date,sea_surface_temp_c,temp_anomaly_c,dhw_c_weeks,bleaching_observed,source\n"
                    "Reef,2026-01-01,29,,,,Field notes\n")
        rows = parse_csv(csv_data.encode())
        result = investigate(rows, "Reef", "2026-01-01", "2026-01-01", "Risk?")
        self.assertEqual(result["risk"], "unknown")

    def test_critic_rejects_unobserved_bleaching_claim(self):
        draft = {"summary": "Confirmed bleaching occurred at Example Reef A.",
                 "risk": "high", "claims": ["Bleaching was observed."],
                 "limitations": ["No direct bleaching observations are available for this selection.",
                                 "The selected dataset is synthetic demonstration data, not a real reef assessment."]}
        with patch.dict("os.environ", {"ORCA_PROVIDER": "gemini", "GEMINI_API_KEY": "test-key"}), \
             patch("orca.workflow._llm", side_effect=[draft, {"approved": True, "feedback": "Looks good"}]):
            result = investigate(SAMPLE, "Example Reef A", "2026-06-01", "2026-07-15", "Is bleaching confirmed?", True)
        self.assertTrue(result["revised"])
        self.assertNotIn("confirmed bleaching", result["summary"].lower())
        self.assertTrue(any(step["action"] == "challenge" for step in result["trace"]))


if __name__ == "__main__":
    unittest.main()
