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

For Gemini reasoning and independent critique, paste your key into the project-root `.env` file after `GEMINI_API_KEY=`. Save the file, then restart the server and select **LLM reasoning & critique**. The evaluation command reads the same file. A populated key in `.env` takes priority over a previously set key in PowerShell. `.env` is excluded from Git; `.env.example` shows the format. Keep the key in this file or your server environment, never in the browser UI.

Alternatively, set a server-side key in the PowerShell session that starts the app:

```powershell
$env:ORCA_PROVIDER = "gemini"
$env:GEMINI_API_KEY = Read-Host "Gemini API key"
$env:ORCA_MODEL = "gemini-3.8-flash"
python -m uvicorn orca.api:app --reload
```

The key stays in the server process and is excluded from Git. For the previous OpenAI option, optionally install the OpenAI Python package and set its server-side key:

```powershell
python -m pip install "openai>=2,<3"
$env:OPENAI_API_KEY = "your-key"
$env:ORCA_PROVIDER = "openai"
$env:ORCA_MODEL = "gpt-4o-mini"
python -m uvicorn orca.api:app --reload
```

Then select **Use LLM reasoning and critique**. Model calls may incur API charges. Gemini uses the Google Gen AI SDK's structured JSON output; OpenAI uses the Responses API. A bounded critic reviews generated claims.

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

## NOAA data and evaluation (phase 2–5)

The two LLM result files include each case's answer for human review. Both modes use the same selected evidence rows and end-to-end latency window. Automated claim support requires an exact match to a canonical evidence-linked finding; paraphrases fail that narrow check even when scientifically valid. Review summaries and claims manually before reporting a winner. Do not commit API keys or raw private input data.

Use **Load NOAA Florida Keys example** for a bundled, offline 12-day excerpt from the [official station archive](https://coralreefwatch.noaa.gov/product/vs/data/florida_keys.txt), 10–21 August 2023. **Refresh from NOAA** downloads a selected period (at most 366 days) from that fixed source. The parser maps `SST@90th_HS` to sea surface temperature, `SSTA@90th_HS` to anomaly, `DHW_from_90th_HS>1` to DHW, and preserves the separate seven-day maximum alert code. Regional virtual station values are satellite heat-stress indicators; they are not direct bleaching observations. Uploaded and imported datasets are kept in server memory until restart.

The API also provides `GET /api/datasets/noaa-offline`, `GET /api/noaa/stations`, and `POST /api/noaa/import` with JSON `station`, `start`, `end`. Claims in the report link to source row IDs. LLM mode uses a reasoner, independent critic, at most one revision, and a verified fallback. It logs latency and actual token counts; dollar cost depends on current model pricing.

Run the reproducible evaluation from the repository root:

```powershell
python -m unittest discover -s tests -v
python -m evaluation.run --output evaluation/baseline_results.json
# Optional with GEMINI_API_KEY and google-genai installed:
python -m evaluation.run --llm --output evaluation/collaborative_results.json
python -m evaluation.run --single-agent --output evaluation/single_agent_results.json
```

The 20-case deterministic result checks implementation behavior against annotated teaching labels; it does not estimate ecological predictive accuracy. The LLM comparison has not been run without an API key. See [SUBMISSION.md](SUBMISSION.md) for methods, limitations, and demo script. The risk labels `<4`, `4–<8`, and `≥8` DHW are educational categories, distinct from NOAA's operational alert codes.
