#!/usr/bin/env python3
"""NovaDev Document Extractor - Vercel ready"""
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from core import extract_to_zip

app = FastAPI(title="NovaDev Document Extractor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static (Vercel public/ akan di-serve otomatis, ini untuk lokal)
static_path = Path(__file__).parent / "public"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).parent / "public" / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>NovaDev Extractor</h1>")


@app.post("/api/extract")
async def extract(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".unity3d"):
        raise HTTPException(400, "File harus berformat .unity3d")

    # Baca full ke memory (Vercel /tmp terbatas, tapi untuk file wajar ok)
    content = await file.read()
    if len(content) > 40 * 1024 * 1024:  # 40MB limit
        raise HTTPException(413, "File terlalu besar (maksimal 40 MB)")

    job_id = str(uuid.uuid4())[:8]
    work = Path(tempfile.gettempdir()) / f"novadev_{job_id}"
    work.mkdir(exist_ok=True)
    zip_path = work / "Document_extracted.zip"

    try:
        result = extract_to_zip(content, zip_path)

        return {
            "success": True,
            "job_id": job_id,
            "extracted": result["ok"],
            "total": result["total"],
            "errors": result["errors"],
            "zip_size": result["zip_size"],
            "zip_md5": result["zip_md5"],
            "download": f"/api/download/{job_id}",
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/download/{job_id}")
async def download(job_id: str):
    zip_path = Path(tempfile.gettempdir()) / f"novadev_{job_id}" / "Document_extracted.zip"
    if not zip_path.exists():
        raise HTTPException(404, "File tidak ditemukan / sudah expired")
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="Document_extracted.zip",
    )


# Untuk Vercel serverless
try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    handler = None
