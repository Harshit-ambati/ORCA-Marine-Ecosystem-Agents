"""Run annotated ORCA cases. LLM results require a server-side API key."""
import argparse
import json
import os
import time
from pathlib import Path

from orca.api import DATASETS
from orca.workflow import PROPOSAL_SCHEMA, _llm
from orca.workflow import investigate

ROOT = Path(__file__).resolve().parent


def evaluate(use_llm=False, single_agent=False):
    cases = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))
    results = []
    for case in cases:
        question = "Assess heat stress and whether bleaching was observed."
        report = investigate(DATASETS[case["dataset"]], case["site"], case["start"], case["end"], question,
                             use_llm and not single_agent)
        if single_agent:
            if not os.getenv("OPENAI_API_KEY"):
                raise RuntimeError("OPENAI_API_KEY is required for single-agent evaluation")
            started = time.perf_counter()
            draft = _llm("single_agent_baseline", {"question": question, "site": case["site"],
                "period": [case["start"], case["end"]], "evidence": report["evidence"]}, PROPOSAL_SCHEMA)
            usage = draft.pop("_usage", {})
            report.update(draft)
            report["revised"] = False
            report["metrics"] = {"calls": 1, **usage,
                "latency_ms": round((time.perf_counter() - started) * 1000, 1),
                "model": os.getenv("ORCA_MODEL", "gpt-4o-mini")}
        ids = {row["id"] for row in report["evidence"]}
        supported = all(set(report["claim_evidence"].get(claim, [])) <= ids and
                        bool(report["claim_evidence"].get(claim)) for claim in report["claims"])
        has_positive_claim = any("Bleaching was recorded" in claim for claim in report["claims"])
        observation_correct = has_positive_claim == (case["observation"] == "positive")
        results.append({"id": case["id"], "risk_correct": report["risk"] == case["expected_risk"],
                        "claims_supported": supported, "observation_correct": observation_correct,
                        "abstention_correct": (report["risk"] == "unknown") == (case["expected_risk"] == "unknown"),
                        "revised": report["revised"], **report["metrics"]})
    count = len(results)
    return {"mode": "single-agent-llm" if single_agent else "collaborative-llm" if use_llm else "deterministic", "cases": count,
            "risk_accuracy": sum(r["risk_correct"] for r in results) / count,
            "claim_support_rate": sum(r["claims_supported"] for r in results) / count,
            "observation_accuracy": sum(r["observation_correct"] for r in results) / count,
            "abstention_accuracy": sum(r["abstention_correct"] for r in results) / count,
            "critic_challenges": sum(r["revised"] for r in results),
            "total_calls": sum(r["calls"] for r in results),
            "total_input_tokens": sum(r["input_tokens"] for r in results),
            "total_output_tokens": sum(r["output_tokens"] for r in results),
            "mean_latency_ms": round(sum(r["latency_ms"] for r in results) / count, 1),
            "details": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--single-agent", action="store_true", help="One LLM call on the same case evidence without specialist claims or critic")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(args.llm, args.single_agent)
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
