"""
MAANAKNETRA — Web Application Backend
FastAPI server serving the Procurement Intelligence API and the Frontend dashboard.
Conforms strictly to contracts/analysis.schema.json and contracts/finding.schema.json.
"""

import os
import sys
import json
import uuid
import shutil
import tempfile
from typing import Dict, Any, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from ai.procurement_analyzer import ProcurementAnalysisEngine

# Initialize FastAPI app
app = FastAPI(
    title="MaanakNetra — AI-Powered Procurement & Indian Standards Intelligence",
    description="Automated audit and tender linter engine for Indian Standards and statutory Quality Control Orders.",
    version="1.0.0",
)

# Enable CORS for local development and deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy singleton for ProcurementAnalysisEngine
_engine_instance: Optional[ProcurementAnalysisEngine] = None
_demo_cache: Optional[Dict[str, Any]] = None


def get_engine() -> ProcurementAnalysisEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ProcurementAnalysisEngine()
    return _engine_instance


@app.get("/health")
def health_check():
    """Health check endpoint for container platforms (Render, Kubernetes, etc.)."""
    return {
        "status": "healthy",
        "service": "MaanakNetra Procurement Intelligence API",
        "version": "1.0.0",
        "engine_ready": _engine_instance is not None,
    }


@app.post("/api/analyze")
async def analyze_tender(file: UploadFile = File(...)):
    """
    Accepts a tender document (PDF, TXT, DOCX), executes end-to-end
    procurement analysis and deterministic tender linting, and returns
    a validated TenderAnalysisResultDocument.
    """
    filename = file.filename or "uploaded_tender.pdf"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in [".pdf", ".txt", ".docx"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Supported formats: .pdf, .txt, .docx",
        )

    # Save uploaded file to secure temporary directory
    temp_dir = tempfile.mkdtemp(prefix="maanaknetra_upload_")
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4().hex}_{filename}")

    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        engine = get_engine()
        result = engine.analyze(
            tender_source=temp_file_path,
            top_k=5,
            document_title=filename,
        )
        return JSONResponse(content=result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error executing tender analysis: {str(e)}",
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
                return JSONResponse(content=_demo_cache)
        except Exception:
            pass

    # Fallback to direct execution
    sample_pdf_path = os.path.join(WORKSPACE_ROOT, "demo", "sample_tender.pdf")
    if not os.path.exists(sample_pdf_path):
        raise HTTPException(status_code=404, detail="demo/sample_tender.pdf not found.")

    engine = get_engine()
    _demo_cache = engine.analyze(sample_pdf_path, top_k=5)
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
