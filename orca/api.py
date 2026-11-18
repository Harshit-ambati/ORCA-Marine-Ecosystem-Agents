"""ORCA HTTP API and static user interface."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .noaa import STATIONS, fetch_station, parse_station_text
from .workflow import DataError, investigate, load_csv, parse_csv

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = load_csv(ROOT / "data" / "sample.csv")
OFFLINE = parse_station_text((ROOT / "data" / "florida_keys_2023_excerpt.txt").read_text(encoding="utf-8"))
DATASETS: dict[str, list[dict]] = {"sample": SAMPLE, "noaa-offline": OFFLINE}
MAX_BYTES = 2_000_000
app = FastAPI(title="ORCA Marine Ecosystem Investigation", version="0.1.0")
app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")


class Investigation(BaseModel):
    dataset_id: str = "sample"
    site: str = Field(min_length=1, max_length=120)
    start: str
    end: str
    question: str = Field(min_length=1, max_length=500)
    use_llm: bool = False


class NOAAImport(BaseModel):
    station: str = "florida_keys"
    start: str
    end: str


@app.get("/")
def home():
    return FileResponse(ROOT / "web" / "index.html")


@app.get("/api/datasets/{dataset_id}")
def dataset(dataset_id: str):
    rows = DATASETS.get(dataset_id)
    if rows is None:
        raise HTTPException(404, "Dataset not found")
    return {"id": dataset_id, "sites": sorted({r["site"] for r in rows}),
            "start": min(r["date"] for r in rows), "end": max(r["date"] for r in rows),
            "rows": len(rows), "synthetic": all(r["source"].lower().startswith("synthetic") for r in rows),
            "source": rows[0]["source"]}


@app.get("/api/noaa/stations")
def noaa_stations():
    return STATIONS


@app.post("/api/noaa/import")
def noaa_import(request: NOAAImport):
    try:
        rows = fetch_station(request.station, request.start, request.end)
    except (DataError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
    identifier = uuid.uuid4().hex
    DATASETS[identifier] = rows
    return dataset(identifier)


@app.post("/api/datasets")
async def upload(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Upload a .csv file")
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "CSV must be at most 2 MB")
    try:
        rows = parse_csv(content)
    except DataError as exc:
        raise HTTPException(400, str(exc)) from exc
    identifier = uuid.uuid4().hex
    DATASETS[identifier] = rows  # Development-only in-memory storage; reset on restart.
    return dataset(identifier)


@app.post("/api/investigate")
def run(request: Investigation):
    rows = DATASETS.get(request.dataset_id)
    if rows is None:
        raise HTTPException(404, "Dataset not found; upload it again after restarting the server")
    try:
        return investigate(rows, request.site, request.start, request.end,
                           request.question, request.use_llm)
    except (DataError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
