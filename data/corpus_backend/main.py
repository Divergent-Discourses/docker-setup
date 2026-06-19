"""
FastAPI app
"""
import io
import os
import csv
import mimetypes
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, Query, BackgroundTasks, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from celery.result import AsyncResult
from tasks import app as celery_app
from tasks import (
    filter_corpus,
    generate_wordcloud_from_csv_path,
    collocations_job,
    preview_tokenised_matches,
    prepare_docs_for_cooccurrence,
    compute_co_occurrences,
    diachronic_analysis,
    )
import tempfile, shutil
import json 

app = FastAPI(title="Corpus Backend", version="0.1")
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
JOB_DIR = os.path.join(os.path.dirname(__file__), "job_storage")
os.makedirs(JOB_DIR, exist_ok=True)


# -----------------------------
# Schemas
# -----------------------------
class FilterRequest(BaseModel):
    region_filter: list[str] = []
    newspaper_filter: list[str] = []
    start_date: str | None = None   # "YYYY‑MM‑DD"
    end_date: str   | None = None
    all_words: str = ""
    any_words: str = ""
    none_words: str = ""

class JobStatus(BaseModel):
    job_id: str
    state: str
    progress: float | None = None   # reserved
    rows: int  | None = None        # reserved


# -----------------------------
# Helper
# -----------------------------
def _save_upload_to_jobfile(upload: UploadFile, suffix: str) -> str:
    job_id = str(uuid.uuid4())
    safe_name = f"{job_id}{suffix}"
    out_path = os.path.join(JOB_DIR, safe_name)
    # stream to disk
    with open(out_path, "wb") as f:
        for chunk in iter(lambda: upload.file.read(1024 * 1024), b""):
            f.write(chunk)
    upload.file.close()
    return job_id, out_path


# -----------------------------
# Filter
# -----------------------------
@app.post("/filter", response_model=JobStatus)
def submit_filter(req: FilterRequest):
    task = filter_corpus.delay(
        req.region_filter,
        req.newspaper_filter,
        req.start_date,
        req.end_date,
        req.all_words,
        req.any_words,
        req.none_words,
    )
    return JobStatus(job_id=task.id, state="PENDING")


# -----------------------------
# Status/Download
# -----------------------------
@app.get("/status/{job_id}", response_model=JobStatus)
def get_status(job_id: str):
    res = AsyncResult(job_id, app=celery_app)
    return JobStatus(job_id=job_id, state=res.state)

@app.get("/download/{job_id}")
def download(job_id: str):
    res = AsyncResult(job_id, app=celery_app)
    if not res.successful():
        raise HTTPException(status_code=400, detail=f"Job {job_id} not ready")
    filepath = res.result
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="File vanished")
    mime, _ = mimetypes.guess_type(filepath)
    return FileResponse(filepath, media_type=mime or "text/csv", filename=os.path.basename(filepath))


@app.get("/preview_result/{job_id}")
def get_preview_result(job_id: str):
    """
    Return JSON preview results if ready.
    """
    res = AsyncResult(job_id, app=celery_app)
    if not res.successful():
        raise HTTPException(status_code=400, detail=f"Job {job_id} not ready")

    filepath = res.result
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="Preview file vanished")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


# -----------------------------
# Wordcloud (file-on-disk)
# -----------------------------
@app.post("/wordcloud", response_model=JobStatus)
async def submit_wordcloud(file: UploadFile = File(...)):
    # Save uploaded CSV to disk, pass path to Celery
    try:
        job_id, csv_path = _save_upload_to_jobfile(file, suffix=".csv")
        task = generate_wordcloud_from_csv_path.delay(csv_path)
        return JobStatus(job_id=task.id, state="PENDING")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Upload failed: {str(e)}")


# -----------------------------
# Preview endpoint
# -----------------------------
@app.post("/preview", response_model=JobStatus)
async def submit_preview(file: UploadFile = File(...), search_term: str = Query(...), limit: int = Query(5, ge=1, le=50)):
    if not search_term.strip():
        raise HTTPException(status_code=400, detail="Must provide a non-empty search_term")

    # Save upload to disk instead of reading to memory
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", dir=JOB_DIR)
    with tmp as buffer:
        shutil.copyfileobj(file.file, buffer)

    task = preview_tokenised_matches.delay(tmp.name, search_term, limit)
    return JobStatus(job_id=task.id, state="PENDING")


# -----------------------------
# Collocations job submit
# -----------------------------
@app.post("/collocations", response_model=JobStatus)
async def submit_collocations(
    file: UploadFile = File(...),
    search_term: Optional[str] = Query(None, description="Optional single token to focus on"),
    top_n: int = Query(50, ge=1, le=200),
):
    """
    Saves the uploaded CSV to disk and dispatches a Celery job.
    The job returns a single CSV with sections:
      - overall_trigram_pos / overall_trigram_neg
      - bigram_pos / bigram_neg (only if search_term provided, stopwords filtered)
      - trigram_pos / trigram_neg (only if search_term provided)
    """
    try:
        job_id, csv_path = _save_upload_to_jobfile(file, suffix=".csv")
        task = collocations_job.delay(csv_path, search_term, top_n)
        return JobStatus(job_id=task.id, state="PENDING")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Upload failed: {str(e)}")


# -----------------------------
# Co-occurrence job submit
# -----------------------------
# --- Upload CSV and prepare docs ---
@app.post("/prepare_docs", response_model=JobStatus)
async def prepare_docs(file: UploadFile = File(...)):
    try:
        job_id, csv_path = _save_upload_to_jobfile(file, ".csv")
        task = prepare_docs_for_cooccurrence.delay(csv_path)
        return JobStatus(job_id=task.id, state="PENDING")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Get result_path ---
@app.get("/result/{job_id}")
def get_result(job_id: str):
    res = AsyncResult(job_id, app=celery_app)
    if not res.successful():
        raise HTTPException(status_code=400, detail=f"Job {job_id} not ready")
    return {"result_path": res.result}


# --- Compute co-occurrences ---
@app.post("/cooccurrence", response_model=JobStatus)
async def cooccurrence(
    docs_path: str = Query(..., description="Path to cached DocBin"),
    search_token: str = Query(...),
    window_size: int = Query(50, ge=1, le=200),
    top_n: int = Query(50, ge=1, le=100)
):
    try:
        task = compute_co_occurrences.delay(docs_path, search_token, window_size, top_n)
        return JobStatus(job_id=task.id, state="PENDING")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------
# Diachronic analysis job submit
# -----------------------------
@app.post("/diachronic", response_model=JobStatus)
async def submit_diachronic(
    file: UploadFile = File(...),
    single_words: str = Query("", description="Comma-separated single words"),
    exact_phrases: str = Query("", description="Comma-separated exact phrases")
):
    """
    Submits a diachronic analysis job.
    """
    try:
        job_id, csv_path = _save_upload_to_jobfile(file, ".csv")
        single_words_list = [w.strip().rstrip("་") for w in single_words.split(",") if w.strip()]
        exact_phrases_list = [p.strip() for p in exact_phrases.split(",") if p.strip()]
        task = diachronic_analysis.delay(csv_path, single_words_list, exact_phrases_list)
        return JobStatus(job_id=task.id, state="PENDING")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
