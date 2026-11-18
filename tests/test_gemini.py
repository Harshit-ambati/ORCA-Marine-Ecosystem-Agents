import json
import os
import sys
import types
import unittest
from unittest.mock import patch

from orca.workflow import PROPOSAL_SCHEMA, _llm, _model_name, _provider


class GeminiAdapterTests(unittest.TestCase):
    def test_structured_response_and_usage(self):
        captured = {}

        class FakeClient:
            def __init__(self, api_key):
                captured["key_set"] = bool(api_key)
                self.models = types.SimpleNamespace(generate_content=self.generate)

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def generate(self, **kwargs):
                captured.update(kwargs)
                return types.SimpleNamespace(text=json.dumps({"summary": "Evidence is incomplete", "risk": "unknown",
                    "claims": [], "limitations": []}), usage_metadata=types.SimpleNamespace(
                    prompt_token_count=42, candidates_token_count=12))

        fake_google = types.ModuleType("google")
        fake_google.genai = types.SimpleNamespace(Client=FakeClient)
        with patch.dict(os.environ, {"ORCA_PROVIDER": "gemini", "GEMINI_API_KEY": "test-only"}), \
             patch.dict(sys.modules, {"google": fake_google}):
            result = _llm("reasoner", {"evidence": []}, PROPOSAL_SCHEMA)
            self.assertEqual(_model_name(), "gemini-3.8-flash")
            self.assertEqual(_provider(), "gemini")
        self.assertTrue(captured["key_set"])
        self.assertEqual(captured["config"]["response_mime_type"], "application/json")
        self.assertEqual(captured["config"]["response_json_schema"], PROPOSAL_SCHEMA)
        self.assertEqual(result["_usage"], {"input_tokens": 42, "output_tokens": 12})
