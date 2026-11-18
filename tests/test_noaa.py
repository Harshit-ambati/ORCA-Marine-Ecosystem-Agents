import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from orca.api import app
from orca.noaa import SOURCE, parse_station_text
from orca.workflow import DataError

TEXT = (Path(__file__).resolve().parents[1] / "data" / "florida_keys_2023_excerpt.txt").read_text(encoding="utf-8")


class NOAATests(unittest.TestCase):
    def test_reproduces_published_values_and_provenance(self):
        rows = parse_station_text(TEXT, start="2023-08-15", end="2023-08-15")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["dhw_c_weeks"], 18.3257)
        self.assertEqual(rows[0]["baa_7d_max"], 6)
        self.assertEqual(rows[0]["source"], SOURCE)
        self.assertIsNone(rows[0]["bleaching_observed"])

    def test_malformed_header_rejected(self):
        with self.assertRaises(DataError):
            parse_station_text(TEXT.replace("BAA_7day_max", "UNKNOWN"))

    def test_api_offline_case(self):
        client = TestClient(app)
        info = client.get("/api/datasets/noaa-offline")
        self.assertEqual(info.status_code, 200)
        self.assertFalse(info.json()["synthetic"])
        result = client.post("/api/investigate", json={"dataset_id": "noaa-offline",
            "site": "Florida Keys", "start": "2023-08-10", "end": "2023-08-21",
            "question": "What is the thermal stress?"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["risk"], "high")
        self.assertTrue(result.json()["claim_evidence"])

    @patch("orca.api.fetch_station")
    def test_live_import_route(self, fetch):
        fetch.return_value = parse_station_text(TEXT)
        response = TestClient(app).post("/api/noaa/import", json={"station": "florida_keys",
            "start": "2023-08-10", "end": "2023-08-21"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["rows"], 12)
