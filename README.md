# ORCA — Marine EcOsystem Reasoning with Collaborative Agents

ORCA is an educational Agentic AI project. It orchestrates specialist agents to investigate coral heat stress, records their evidence and critique, and produces a traceable report. See [WORKPLAN.md](WORKPLAN.md) for milestones and evaluation.

## Run locally (Windows PowerShell)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn orca.api:app --reload
```

Open **http://127.0.0.1:8000**. Choose an example site, dates, and a question. The sample dataset is synthetic. Without an LLM key, the application executes a deterministic, evidence-first **demo workflow**; it is not represented as an LLM run.

For LLM reasoning and independent critique, optionally install the OpenAI Python package and set a server-side key:

```powershell
python -m pip install "openai>=2,<3"
$env:OPENAI_API_KEY = "your-key"
$env:ORCA_MODEL = "gpt-4o-mini"
python -m uvicorn orca.api:app --reload
```

Then select **Use LLM reasoning and critique**. Model calls incur API charges. The key stays on the server. The implementation uses the Responses API with structured JSON output and a bounded critic step. The critic cannot silently turn missing observations into confirmed bleaching.

## Import data

Upload a UTF-8 CSV under 2 MB with these columns:

| Column | Meaning |
| --- | --- |
| `site` | Site name, consistent across rows |
| `date` | ISO date, `YYYY-MM-DD` |
| `sea_surface_temp_c` | Sea surface temperature in °C; blank allowed |
| `temp_anomaly_c` | Temperature anomaly in °C; blank allowed |
| `dhw_c_weeks` | Nonnegative Degree Heating Weeks in °C-weeks; blank allowed |
| `bleaching_observed` | `true`, `false`, or blank for no observation |
| `source` | Dataset or observation provenance |

The example file is [data/sample.csv](data/sample.csv). Uploaded rows are held in memory for this development prototype and are lost when the server restarts. A real-data adapter and documented source metadata are next milestones. CSV values should be mapped to one consistent geographic site and compatible time period before drawing conclusions.

## API

- `GET /api/datasets/sample` — sites and time range.
- `POST /api/datasets` — multipart upload with field `file`.
- `POST /api/investigate` — JSON body: `dataset_id`, `site`, `start`, `end`, `question`, `use_llm`.
- `GET /docs` — interactive API documentation.

## Structure

```text
orca/workflow.py   CSV validation, specialist analyses, LLM roles, critic, trace
orca/api.py        FastAPI routes and static UI delivery
web/               HTML, CSS, JavaScript frontend
data/sample.csv    Explicitly synthetic demonstration records
tests/             Focused workflow and API checks
WORKPLAN.md        Research plan, milestones, and evaluation
```

## Scientific boundaries

The demo DHW categories are a teaching heuristic (`<4` low, `4–<8` moderate, `≥8` high) and do not reproduce a full operational alert system. A DHW signal indicates thermal stress, while a direct observation is needed to say bleaching was observed. The model may suggest explanations but its output is reviewed against the provided evidence. Verify real data provenance, spatial resolution, dates, and thresholds before presenting scientific conclusions.

Useful source starting points: [NOAA Coral Reef Watch products](https://www.coralreefwatch.noaa.gov/product/index.php), [NOAA 5 km methodology](https://www.coralreefwatch.noaa.gov/product/5km/methodology.php), [OBIS data access](https://manual.obis.org/access).
