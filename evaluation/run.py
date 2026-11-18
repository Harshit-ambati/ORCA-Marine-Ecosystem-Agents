"""Run annotated ORCA cases. LLM results require a server-side API key."""
import argparse
import json
import os
import time
from pathlib import Path

from orca.api import DATASETS
from orca.workflow import PROPOSAL_SCHEMA, _llm, _model_name, _provider
from orca.workflow import investigate

ROOT = Path(__file__).resolve().parent


def score_report(report, case, canonical_claims):
    """Score explicit, exact evidence claims; prose is retained for human review."""
    ids = {row["id"] for row in report["evidence"]}
    claims = report["claims"]
    supported = all(
        claim in canonical_claims
        and bool(canonical_claims[claim])
        and set(canonical_claims[claim]) <= ids
        and set(report["claim_evidence"].get(claim, [])) == set(canonical_claims[claim])
        for claim in claims
    )
    positive_claims = {claim for claim in canonical_claims if claim.startswith("Bleaching was recorded on ")}
    has_positive_claim = any(claim in positive_claims for claim in claims)
    unsupported_observation = case["observation"] != "positive" and any(
        phrase in report["summary"].lower()
        for phrase in ("bleaching occurred", "bleaching was observed", "confirmed bleaching", "coral has bleached")
    )
    return {
        "risk_correct": report["risk"] == case["expected_risk"],
        "claims_supported": supported,
        "observation_correct": has_positive_claim == (case["observation"] == "positive") and not unsupported_observation,
        "abstention_correct": (report["risk"] == "unknown") == (case["expected_risk"] == "unknown"),
    }


def evaluate(use_llm=False, single_agent=False):
    cases = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))
    results = []
    for case in cases:
        started = time.perf_counter()
        question = "Assess heat stress and whether bleaching was observed."
        report = investigate(DATASETS[case["dataset"]], case["site"], case["start"], case["end"], question,
                             use_llm and not single_agent)
        canonical_claims = dict(report["claim_evidence"])
        if single_agent:
            if not os.getenv("GEMINI_API_KEY" if _provider() == "gemini" else "OPENAI_API_KEY"):
                raise RuntimeError("The selected provider's API key is required for single-agent evaluation")
            draft = _llm("single_agent_baseline", {"question": question, "site": case["site"],
                "period": [case["start"], case["end"]], "evidence": report["evidence"]}, PROPOSAL_SCHEMA)
            usage = draft.pop("_usage", {})
            report.update(draft)
            report["claim_evidence"] = {claim: canonical_claims[claim] for claim in draft["claims"]
                                        if claim in canonical_claims}
            report["revised"] = False
            report["metrics"] = {"calls": 1, **usage,
                "model": _model_name(), "provider": _provider()}
        report["metrics"]["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
        results.append({"id": case["id"], "dataset": case["dataset"],
                        **score_report(report, case, canonical_claims),
                        "revised": report["revised"], **report["metrics"],
                        "answer": {key: report[key] for key in ("risk", "summary", "claims", "limitations")}})
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
