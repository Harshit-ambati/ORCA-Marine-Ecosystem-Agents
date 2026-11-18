# ORCA work plan

**Project:** Marine EcOsystem Reasoning with Collaborative Agents  
**Course focus:** Agentic AI and LLMs

## Research question

Can a coordinated group of tool-using agents produce better supported marine ecosystem investigations than a single LLM response?

The first case study is coral heat stress. ORCA investigates a selected reef and period, reviews environmental measurements and observation records, proposes a finding, challenges unsupported claims, and produces an evidence-linked report. A heat-stress signal is a risk indicator; it is not proof that bleaching occurred.

## Agent workflow

1. **Coordinator** interprets the question, sets the selected site and date window, and sends tasks to specialists.
2. **Ocean Data Agent** retrieves rows, checks units and missing data, and calculates temperature anomaly and maximum Degree Heating Weeks (DHW).
3. **Biodiversity Agent** checks observation coverage and records whether bleaching observations exist. An absent record is reported as missing evidence, not as evidence of absence.
4. **Reasoning Agent** proposes a conclusion from the specialists' structured findings. With an API key it uses an LLM; otherwise the demo runs a transparent rule-based baseline.
5. **Critic Agent** examines the proposed conclusion and evidence. It can request a revision when a claim overstates the data. A separate LLM critique is available, and hard evidence checks always run.
6. **Coordinator** orders one revision when needed. **Report Agent** returns the final explanation and a trace of every exchange.

## Milestones

| Milestone | Deliverable | Completion check |
| --- | --- | --- |
| 1. Working foundation | CSV ingestion, API, agent state, trace, browser UI | Run an investigation on sample data and on an uploaded CSV |
| 2. Real evidence | Import a documented NOAA heat-stress export and site observations; preserve provenance | Reproduce source values for several site/date windows |
| 3. LLM collaboration | Structured prompts, retries, critic revision, cost and latency logs | Compare the first proposal with the final reviewed answer |
| 4. Evaluation | Curated questions, expected claims, single-agent baseline | Report accuracy, citation support, abstention, latency, and cost |
| 5. University submission | README, methods, limitations, demo, slides, report | A reviewer can reproduce the demo and results |

## Evaluation design

- Build at least 20 cases: clear heat stress, low stress, missing measurements, conflicting observations, and out-of-range questions.
- Annotate expected risk label and which claims are supported by source rows.
- Compare ORCA against a single LLM given the same evidence and against the rule-based baseline.
- Measure supported-claim rate, risk-label accuracy, appropriate abstention, critic correction rate, latency, and API cost.
- Keep test and evaluation data separate from prompt examples. Record model, prompt version, data version, and run date.

## Scope and limitations

The included CSV is synthetic demonstration data, not a scientific dataset. The initial risk thresholds are an illustrative teaching rule and must be reviewed against the intended source methodology before scientific use. Site observation records and satellite heat-stress pixels may have different coverage and times. ORCA must show that limitation and avoid causal or confirmed bleaching claims without direct observations.

## Next decisions

- Select a real study region, source files, and assignment rubric.
- Decide whether the final deliverable requires live data, offline reproducibility, or both.
- Define the evaluation rubric with the supervisor before reporting performance.
