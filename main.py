#!/usr/bin/env python3
"""NovaDev Document Extractor - Vercel ready"""
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from core import extract_to_zip

app = FastAPI(title="NovaDev Document Extractor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HTML_PAGE = r'''<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>NovaDev — Document Extractor</title>
  <style>
    :root {
      --bg: #0c0c0e;
      --surface: #16161a;
      --border: #2a2a30;
      --text: #e8e6e3;
      --muted: #8a8780;
      --accent: #c23b3b;
      --accent-dim: #8a2a2a;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      line-height: 1.5;
    }
    .banner {
      width: 100%;
      max-width: 720px;
      margin: 2.5rem auto 1.5rem;
      border-radius: 4px;
      overflow: hidden;
      box-shadow: 0 12px 40px rgba(0,0,0,0.55);
    }
    .banner img { width: 100%; display: block; object-fit: cover; }
    header { text-align: center; margin-bottom: 2rem; }
    header h1 {
      font-size: 1.35rem;
      font-weight: 600;
      letter-spacing: 0.04em;
    }
    header p { font-size: 0.85rem; color: var(--muted); margin-top: 0.35rem; }
    main { width: 100%; max-width: 420px; padding: 0 1.25rem 3rem; }
    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 1.75rem;
    }
    .dropzone {
      border: 1.5px dashed var(--border);
      border-radius: 5px;
      padding: 2rem 1rem;
      text-align: center;
      cursor: pointer;
      transition: border-color 0.2s, background 0.2s;
      position: relative;
    }
    .dropzone:hover, .dropzone.drag {
      border-color: var(--accent);
      background: rgba(194, 59, 59, 0.06);
    }
    .dropzone input {
      position: absolute; inset: 0; opacity: 0; cursor: pointer;
    }
    .dropzone .label { font-size: 0.9rem; color: var(--muted); }
    .dropzone .filename {
      margin-top: 0.6rem; font-size: 0.8rem; color: var(--text); word-break: break-all;
    }
    button {
      width: 100%; margin-top: 1.25rem; padding: 0.75rem;
      background: var(--accent); color: #fff; border: none;
      border-radius: 5px; font-size: 0.95rem; font-weight: 500;
      cursor: pointer; transition: background 0.2s;
    }
    button:hover:not(:disabled) { background: #d44545; }
    button:disabled { background: var(--accent-dim); cursor: not-allowed; opacity: 0.7; }
    .progress { display: none; margin-top: 1.25rem; }
    .progress.active { display: block; }
    .bar { height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; }
    .bar > div { height: 100%; width: 0%; background: var(--accent); transition: width 0.3s ease; }
    .status { font-size: 0.8rem; color: var(--muted); margin-top: 0.5rem; text-align: center; }
    .result {
      display: none; margin-top: 1.5rem; padding-top: 1.25rem;
      border-top: 1px solid var(--border); text-align: center;
    }
    .result.show { display: block; }
    .result a {
      display: inline-block; margin-top: 0.75rem; padding: 0.6rem 1.4rem;
      background: transparent; border: 1px solid var(--accent);
      color: var(--accent); border-radius: 5px; text-decoration: none;
      font-size: 0.9rem; transition: background 0.2s, color 0.2s;
    }
    .result a:hover { background: var(--accent); color: #fff; }
    .meta { font-size: 0.78rem; color: var(--muted); margin-top: 0.6rem; }
    footer {
      margin-top: auto; padding: 1.5rem;
      font-size: 0.75rem; color: var(--muted); letter-spacing: 0.05em;
    }
  </style>
</head>
<body>
  <div class="banner">
    <img src="/banner.png" alt="NovaDev" />
  </div>

  <header>
    <h1>DOCUMENT EXTRACTOR</h1>
    <p>MLBB Bundle · Extract & Download</p>
  </header>

  <main>
    <div class="card">
      <div class="dropzone" id="zone">
        <input type="file" id="file" accept=".unity3d" />
        <div class="label">Drop Document.unity3d di sini<br>atau klik untuk pilih<br><small style="opacity:0.7">Format .unity3d · Maks. 40 MB</small></div>
        <div class="filename" id="fname"></div>
      </div>

      <button id="btn" disabled>Extract</button>

      <div class="progress" id="prog">
        <div class="bar"><div id="bar"></div></div>
        <div class="status" id="status">Mengunggah...</div>
      </div>

      <div class="result" id="result">
        <div id="summary"></div>
        <a id="dl" href="#">Download .zip</a>
        <div class="meta" id="meta"></div>
      </div>
    </div>
  </main>

  <footer>NOVADEV</footer>

  <script>
    const zone = document.getElementById("zone");
    const fileInput = document.getElementById("file");
    const fname = document.getElementById("fname");
    const btn = document.getElementById("btn");
    const prog = document.getElementById("prog");
    const bar = document.getElementById("bar");
    const status = document.getElementById("status");
    const result = document.getElementById("result");
    const summary = document.getElementById("summary");
    const dl = document.getElementById("dl");
    const meta = document.getElementById("meta");

    let selected = null;

    zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("drag"); });
    zone.addEventListener("dragleave", () => zone.classList.remove("drag"));
    zone.addEventListener("drop", e => {
      e.preventDefault();
      zone.classList.remove("drag");
      if (e.dataTransfer.files.length) setFile(e.dataTransfer.files[0]);
    });

    fileInput.addEventListener("change", () => {
      if (fileInput.files.length) setFile(fileInput.files[0]);
    });

    function setFile(f) {
      if (!f.name.toLowerCase().endsWith(".unity3d")) {
        fname.textContent = "File harus berformat .unity3d";
        selected = null;
        btn.disabled = true;
        return;
      }
      if (f.size > 40 * 1024 * 1024) {
        fname.textContent = "File terlalu besar (maks. 40 MB)";
        selected = null;
        btn.disabled = true;
        return;
      }
      selected = f;
      fname.textContent = f.name + " (" + (f.size / 1024 / 1024).toFixed(1) + " MB)";
      btn.disabled = false;
      result.classList.remove("show");
    }

    btn.addEventListener("click", async () => {
      if (!selected) return;

      btn.disabled = true;
      prog.classList.add("active");
      result.classList.remove("show");
      bar.style.width = "15%";
      status.textContent = "Mengunggah...";

      const fd = new FormData();
      fd.append("file", selected);

      try {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/extract");

        xhr.upload.onprogress = e => {
          if (e.lengthComputable) {
            const pct = Math.min(70, Math.round((e.loaded / e.total) * 70));
            bar.style.width = pct + "%";
            status.textContent = "Mengunggah... " + pct + "%";
          }
        };

        const res = await new Promise((resolve, reject) => {
          xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              resolve(JSON.parse(xhr.responseText));
            } else {
              try {
                reject(JSON.parse(xhr.responseText).detail || "Error");
              } catch {
                reject("Server error");
              }
            }
          };
          xhr.onerror = () => reject("Koneksi gagal");
          xhr.send(fd);
        });

        bar.style.width = "100%";
        status.textContent = "Selesai";

        summary.textContent = `Extracted ${res.extracted}/${res.total} file`;
        dl.href = res.download;
        let info = (res.zip_size / 1024 / 1024).toFixed(2) + " MB";
        if (res.zip_md5) info += " · MD5 " + res.zip_md5.slice(0, 8) + "...";
        if (res.errors && res.errors.length) info += " · " + res.errors.length + " error";
        meta.textContent = info;
        result.classList.add("show");
      } catch (err) {
        status.textContent = "Gagal: " + err;
        bar.style.width = "0%";
      } finally {
        btn.disabled = false;
      }
    });
  </script>
</body>
</html>
'''


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(HTML_PAGE)


@app.post("/api/extract")
async def extract(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".unity3d"):
        raise HTTPException(400, "File harus berformat .unity3d")

    content = await file.read()
    if len(content) > 40 * 1024 * 1024:
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


# Vercel serverless entry
try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    handler = None
