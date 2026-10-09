"""
MAANAKNETRA — Web Application Backend
FastAPI server serving the Procurement Intelligence API and the Frontend dashboard.
Conforms strictly to contracts/analysis.schema.json and contracts/finding.schema.json.
"""

import os
# Pin CPU threads and disable CUDA driver allocations to minimize RAM on 512MB hosts
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import sys
import json
import uuid
import time
import shutil
import tempfile
import traceback
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from starlette.concurrency import run_in_threadpool

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from ai.procurement_analyzer import ProcurementAnalysisEngine

# Lazy singleton for ProcurementAnalysisEngine
_engine_instance: Optional[ProcurementAnalysisEngine] = None
_demo_cache: Optional[Dict[str, Any]] = None


def get_engine() -> ProcurementAnalysisEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ProcurementAnalysisEngine()
    return _engine_instance


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan handler.
    The analysis engine initializes lazily on the first analysis request.
    """
    print(
        "[STARTUP] MaanakNetra backend ready; "
        "analysis engine will initialize on demand.",
        flush=True,
    )
    yield


# Initialize FastAPI app
app = FastAPI(
    title="MaanakNetra — AI-Powered Procurement & Indian Standards Intelligence",
    description="Automated audit and tender linter engine for Indian Standards and statutory Quality Control Orders.",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS for application origin
ALLOWED_ORIGINS_ENV = os.environ.get("CORS_ORIGINS", "")
if ALLOWED_ORIGINS_ENV:
    ALLOWED_ORIGINS = [orig.strip() for orig in ALLOWED_ORIGINS_ENV.split(",") if orig.strip()]
else:
    ALLOWED_ORIGINS = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

CACHE_DIR = os.path.join(WORKSPACE_ROOT, ".cache")
ANALYSES_DIR = os.path.join(CACHE_DIR, "analyses")
HISTORY_FILE = os.path.join(CACHE_DIR, "analyses_history.json")
DECISIONS_FILE = os.path.join(CACHE_DIR, "officer_decisions.json")

os.makedirs(ANALYSES_DIR, exist_ok=True)


def get_catalogue_metadata() -> Dict[str, Any]:
    """Extracts ground-truth catalogue statistics from data/standards.json and data/relations.json."""
    standards_path = os.path.join(WORKSPACE_ROOT, "data", "standards.json")
    relations_path = os.path.join(WORKSPACE_ROOT, "data", "relations.json")
    standards = []
    relations = []
    if os.path.exists(standards_path):
        with open(standards_path, "r", encoding="utf-8") as f:
            standards = json.load(f)
    if os.path.exists(relations_path):
        with open(relations_path, "r", encoding="utf-8") as f:
            relations = json.load(f)

    categories = sorted(list({s.get("category", "") for s in standards if s.get("category")}))
    verified_count = sum(
        1 for s in standards
        if s.get("verification", {}).get("verification_status") in ["VERIFIED_OFFICIAL", "VERIFIED"]
        or s.get("verification_status") in ["VERIFIED_OFFICIAL", "VERIFIED"]
    )
    unverified_count = len(standards) - verified_count

    std_nums = {s.get("is_number") for s in standards}
    unresolved_count = sum(
        1 for r in relations
        if r.get("source") not in std_nums or r.get("target") not in std_nums
    )

    return {
        "standards_count": len(standards),
        "categories_count": len(categories),
        "categories": categories,
        "relations_count": len(relations),
        "unresolved_references": unresolved_count,
        "verified_count": verified_count,
        "unverified_count": unverified_count,
    }


def record_analysis_in_history(result: Dict[str, Any]):
    """Persists real completed analysis to disk for history and retrieval."""
    meta = result.get("tender_metadata", {})
    analysis_id = meta.get("analysis_id")
    if not analysis_id:
        return

    # Save full dossier
    dossier_path = os.path.join(ANALYSES_DIR, f"{analysis_id}.json")
    with open(dossier_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Update summary list
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    existing_idx = next((i for i, h in enumerate(history) if h.get("analysis_id") == analysis_id), None)
    summary_entry = {
        "analysis_id": analysis_id,
        "document_title": meta.get("document_title", "Tender Document"),
        "file_name": meta.get("file_name", "tender.pdf"),
        "analyzed_at": meta.get("analyzed_at", time.strftime("%Y-%m-%dT%H:%M:%SZ")),
        "status": result.get("status", "completed"),
        "requirements_count": len(result.get("extracted_requirements", [])),
        "findings_count": len(result.get("findings", [])),
        "risk_level": result.get("risk_indicator", {}).get("risk_level", "LOW"),
        "compliance_score": result.get("risk_indicator", {}).get("compliance_score", 100.0),
    }

    if existing_idx is not None:
        history[existing_idx] = summary_entry
    else:
        history.insert(0, summary_entry)

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


@app.get("/health")
def health_check():
    """Exposes server status, pre-warmed model state, and real catalogue sizing."""
    meta = get_catalogue_metadata()
    return {
        "status": "healthy",
        "service": "MaanakNetra Procurement Intelligence API",
        "version": "1.0.0",
        "model_loaded": _engine_instance is not None,
        "catalogue_size": meta["standards_count"],
        "covered_categories_count": meta["categories_count"],
    }


@app.get("/api/catalogue/stats")
def get_catalogue_stats():
    """Returns verified standards catalogue statistics."""
    return get_catalogue_metadata()


@app.get("/api/analyses")
def list_analyses():
    """Returns persistent list of completed tender analyses from disk."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


@app.get("/api/analyses/{analysis_id}")
def get_analysis_dossier(analysis_id: str):
    """Returns full auditable procurement intelligence dossier for an analysis ID."""
    dossier_path = os.path.join(ANALYSES_DIR, f"{analysis_id}.json")
    if not os.path.exists(dossier_path):
        if analysis_id in ["CANONICAL_DEMO", "DEMO_SAMPLE"]:
            return get_canonical_demo()
        return JSONResponse(
            status_code=404,
            content={
                "error_code": "ANALYSIS_NOT_FOUND",
                "message": f"Analysis with ID '{analysis_id}' was not found in storage.",
                "stage": "Retrieving analysis dossier",
            }
        )
    try:
        with open(dossier_path, "r", encoding="utf-8") as f:
            return JSONResponse(content=json.load(f))
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "DOSSIER_READ_ERROR",
                "message": f"Failed to load analysis dossier: {str(e)}",
                "stage": "Retrieving analysis dossier",
            }
        )


@app.post("/api/decisions")
async def save_officer_decision(payload: Dict[str, Any]):
    """Persists technical procurement officer decisions for audit findings."""
    analysis_id = payload.get("analysis_id")
    finding_id = payload.get("finding_id")
    decision = payload.get("decision")
    notes = payload.get("notes", "")

    if not analysis_id or not finding_id or not decision:
        return JSONResponse(
            status_code=400,
            content={
                "error_code": "INVALID_DECISION_PAYLOAD",
                "message": "analysis_id, finding_id, and decision ('ACCEPTED' | 'DISMISSED' | 'REVIEWED') are required.",
                "stage": "Officer Decision",
            }
        )

    decision_norm = str(decision).upper()
    if decision_norm not in ["ACCEPTED", "DISMISSED", "REVIEWED"]:
        return JSONResponse(
            status_code=400,
            content={
                "error_code": "INVALID_DECISION_VALUE",
                "message": f"Invalid decision value '{decision}'. Must be ACCEPTED, DISMISSED, or REVIEWED.",
                "stage": "Officer Decision",
            }
        )

    decisions = {}
    if os.path.exists(DECISIONS_FILE):
        try:
            with open(DECISIONS_FILE, "r", encoding="utf-8") as f:
                decisions = json.load(f)
        except Exception:
            decisions = {}

    if analysis_id not in decisions:
        decisions[analysis_id] = {}

    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    decisions[analysis_id][finding_id] = {
        "decision": decision_norm,
        "notes": notes,
        "timestamp": ts,
        "officer": "Technical Procurement Officer",
    }

    with open(DECISIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(decisions, f, indent=2, ensure_ascii=False)

    return {
        "status": "success",
        "analysis_id": analysis_id,
        "finding_id": finding_id,
        "decision": decision_norm,
        "timestamp": ts,
    }


@app.get("/api/decisions/{analysis_id}")
def get_officer_decisions(analysis_id: str):
    """Retrieves all saved officer decisions for a given analysis ID."""
    if not os.path.exists(DECISIONS_FILE):
        return {"analysis_id": analysis_id, "decisions": {}}
    try:
        with open(DECISIONS_FILE, "r", encoding="utf-8") as f:
            all_decisions = json.load(f)
        return {
            "analysis_id": analysis_id,
            "decisions": all_decisions.get(analysis_id, {}),
        }
    except Exception:
        return {"analysis_id": analysis_id, "decisions": {}}


def _execute_analysis_task(temp_file_path: str, filename: str) -> Dict[str, Any]:
    """Synchronous CPU worker executed in Starlette threadpool."""
    engine = get_engine()
    try:
        res = engine.analyze(
            tender_source=temp_file_path,
            top_k=5,
            document_title=filename,
        )
    except Exception as e:
        print(f"[ANALYZE] Analysis worker encountered error ({e}). Activating emergency fallback.", flush=True)
        res = engine.build_emergency_fallback(
            tender_source=temp_file_path,
            document_title=filename,
            error_context=e,
        )
    # Save to history
    record_analysis_in_history(res)
    return res


@app.post("/api/analyze")
async def analyze_tender(file: UploadFile = File(...)):
    """
    Accepts a tender document (PDF, TXT, DOCX), executes end-to-end
    procurement analysis and deterministic tender linting, and returns
    a validated TenderAnalysisResultDocument conforming to contracts/analysis.schema.json.
    """
    t_start = time.time()
    filename = file.filename or "uploaded_tender.pdf"
    clean_filename = os.path.basename(filename).replace("..", "").replace("/", "").replace("\\", "")
    print(f"[ANALYZE] upload received: {clean_filename}", flush=True)

    ext = os.path.splitext(clean_filename)[1].lower()
    if ext not in [".pdf", ".txt", ".docx"]:
        print(f"[ANALYZE] file validation failed: Unsupported format '{ext}'", flush=True)
        return JSONResponse(
            status_code=400,
            content={
                "error_code": "UNSUPPORTED_FILE_TYPE",
                "message": f"Unsupported file format '{ext}'. Supported formats: .pdf, .docx, .txt",
                "stage": "Parsing tender",
            }
        )

    # Save uploaded file to secure temporary directory
    temp_dir = tempfile.mkdtemp(prefix="maanaknetra_upload_")
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4().hex}_{clean_filename}")

    try:
        # Buffer upload stream
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(temp_file_path)
        print(f"[ANALYZE] file validated: {clean_filename} ({file_size} bytes)", flush=True)

        if file_size == 0:
            return JSONResponse(
                status_code=422,
                content={
                    "error_code": "EMPTY_FILE",
                    "message": "Uploaded file is empty (0 bytes). Please upload a valid procurement tender document.",
                    "stage": "Parsing tender",
                }
            )

        if file_size > 25 * 1024 * 1024:
            return JSONResponse(
                status_code=413,
                content={
                    "error_code": "FILE_TOO_LARGE",
                    "message": f"File size ({round(file_size / (1024*1024), 2)}MB) exceeds 25MB limit.",
                    "stage": "Parsing tender",
                }
            )

        # Offload CPU-bound analysis to threadpool so the asyncio event loop remains 100% responsive
        result = await run_in_threadpool(_execute_analysis_task, temp_file_path, clean_filename)
        duration = round(time.time() - t_start, 2)
        print(f"[ANALYZE] response returned: HTTP 200 in {duration}s", flush=True)
        return JSONResponse(content=result)

    except ValueError as ve:
        duration = round(time.time() - t_start, 2)
        print(f"[ANALYZE] text extraction failed after {duration}s: {ve}", flush=True)
        return JSONResponse(
            status_code=422,
            content={
                "error_code": "NO_READABLE_TEXT",
                "message": str(ve),
                "stage": "Reading document",
            }
        )

    except TimeoutError:
        duration = round(time.time() - t_start, 2)
        return JSONResponse(
            status_code=504,
            content={
                "error_code": "PROCESSING_TIMEOUT",
                "message": f"Tender analysis timed out after {duration}s.",
                "stage": "Tender analysis",
            }
        )

    except Exception as e:
        traceback.print_exc()
        duration = round(time.time() - t_start, 2)
        print(f"[ANALYZE] processing failed after {duration}s: {e}. Generating safe fallback.", flush=True)
        try:
            fallback_res = get_engine().build_emergency_fallback(
                tender_source=temp_file_path if os.path.exists(temp_file_path) else clean_filename,
                document_title=clean_filename,
                error_context=e,
            )
            record_analysis_in_history(fallback_res)
            return JSONResponse(content=fallback_res)
        except Exception as fb_err:
            print(f"[ANALYZE] Emergency fallback failed: {fb_err}", flush=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "message": f"Error executing tender analysis: {str(e)}",
                    "stage": "Executing Technical Procurement Audit",
                }
            )
    finally:
        # Clean up temporary file and directory
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass


@app.get("/api/demo")
def get_canonical_demo():
    """
    Returns the real end-to-end audit result for demo/sample_tender.pdf.
    Uses memory cache or cached JSON artifact if available, or executes the engine.
    Never returns hardcoded or fabricated facts.
    """
    global _demo_cache

    if _demo_cache is not None:
        return JSONResponse(content=_demo_cache)

    demo_json_path = os.path.join(WORKSPACE_ROOT, "demo", "tender_analysis_result.json")
    if os.path.exists(demo_json_path):
        try:
            with open(demo_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                _demo_cache = data
                record_analysis_in_history(data)
                return JSONResponse(content=_demo_cache)
        except Exception:
            pass

    # Fallback to direct execution
    sample_pdf_path = os.path.join(WORKSPACE_ROOT, "demo", "sample_tender.pdf")
    if not os.path.exists(sample_pdf_path):
        raise HTTPException(status_code=404, detail="demo/sample_tender.pdf not found.")

    engine = get_engine()
    _demo_cache = engine.analyze(sample_pdf_path, top_k=5)
    record_analysis_in_history(_demo_cache)
    return JSONResponse(content=_demo_cache)


# Mount static frontend directory
FRONTEND_DIR = os.path.join(WORKSPACE_ROOT, "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    print(f"Starting MaanakNetra Web Server on http://{host}:{port}")
    uvicorn.run("backend.app:app", host=host, port=port, reload=False)

