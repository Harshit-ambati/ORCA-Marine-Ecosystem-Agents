import unittest

from evaluation.run import score_report


class EvaluationScoringTests(unittest.TestCase):
    def setUp(self):
        self.claim = "Bleaching was recorded on 2026-06-01."
        self.canonical = {self.claim: ["row-2"]}
        self.case = {"expected_risk": "moderate", "observation": "positive"}
        self.report = {
            "risk": "moderate", "summary": "Heat stress is elevated.",
            "claims": [self.claim], "claim_evidence": {self.claim: ["row-2"]},
            "evidence": [{"id": "row-2"}],
        }

    def test_grounded_observation_passes(self):
        result = score_report(self.report, self.case, self.canonical)
        self.assertTrue(result["claims_supported"])
        self.assertTrue(result["observation_correct"])

    def test_unmatched_claim_fails_support(self):
        self.report["claims"] = ["Bleaching was recorded somewhere."]
        self.report["claim_evidence"] = {}
        result = score_report(self.report, self.case, self.canonical)
        self.assertFalse(result["claims_supported"])
        self.assertFalse(result["observation_correct"])

    def test_summary_cannot_claim_unobserved_bleaching(self):
        self.case["observation"] = "missing"
        self.report["summary"] = "Confirmed bleaching occurred."
        self.report["claims"] = []
        result = score_report(self.report, self.case, self.canonical)
        self.assertFalse(result["observation_correct"])


if __name__ == "__main__":
    unittest.main()
