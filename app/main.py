"""
FastAPI entrypoint.
Local:  uvicorn app.main:app --reload  → http://localhost:8000
Vercel: auto-served via api/index.py
"""
import os
import time
import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from collections import defaultdict
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.schemas import CoverLetterRequest, HealthResponse
from app.prompts import SYSTEM_PROMPT, build_user_prompt
from app.llm_client import generate_cover_letter, verify_api_key, GroqError, MODEL

logger = logging.getLogger("coverletter.api")

app = FastAPI(title="Cover Letter Pro")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "DELETE"],
    allow_headers=["*"],
)

# Rate limiter: 10 requests per minute per IP
_request_log: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 10
WINDOW_SECONDS = 60

# History — file-based locally, in-memory on Vercel (no persistent filesystem)
HISTORY_FILE = Path("cover_letter_history.json")
_memory_history: list = []          # fallback when filesystem is read-only
_USE_FILE = True                    # will be set to False if file write fails


def _check_rate_limit(ip: str) -> None:
    now = time.time()
    recent = [t for t in _request_log[ip] if now - t < WINDOW_SECONDS]
    if len(recent) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Too many requests. Try again shortly.")
    recent.append(now)
    _request_log[ip] = recent


def _load_history() -> list:
    global _USE_FILE
    if not _USE_FILE:
        return list(_memory_history)
    try:
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    except Exception:
        _USE_FILE = False
        return list(_memory_history)


def _save_to_history(entry: dict) -> None:
    global _USE_FILE
    if not _USE_FILE:
        _memory_history.insert(0, entry)
        return
    try:
        history = _load_history()
        history.insert(0, entry)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        _USE_FILE = False
        _memory_history.insert(0, entry)


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", model=MODEL)


@app.post("/generate")
def generate(req: CoverLetterRequest, request: Request):
    _check_rate_limit(request.client.host)

    user_prompt = build_user_prompt(
        job_title=req.job_title,
        company_name=req.company_name,
        job_description=req.job_description,
        candidate_background=req.candidate_background,
        tone=req.tone,
        word_limit=req.word_limit,
        language=req.language,
    )

    try:
        letter_text = generate_cover_letter(SYSTEM_PROMPT, user_prompt)
    except GroqError as exc:
        logger.error("Groq generation failed: %s", exc)
        error_body = {"error": str(exc)}
        if exc.suggestion:
            error_body["suggestion"] = exc.suggestion
        return JSONResponse(error_body, status_code=exc.status_code)

    word_count = len(letter_text.split())

    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "job_title": req.job_title,
        "company_name": req.company_name,
        "tone": req.tone,
        "language": req.language,
        "word_limit": req.word_limit,
        "word_count": word_count,
        "letter": letter_text,
    }
    _save_to_history(entry)

    return JSONResponse({
        "letter": letter_text,
        "word_count": word_count,
        "id": entry["id"],
    })


@app.get("/debug/verify-key")
def debug_verify_key():
    try:
        result = verify_api_key()
        return JSONResponse(result)
    except GroqError as exc:
        error_body = {"error": str(exc)}
        if exc.suggestion:
            error_body["suggestion"] = exc.suggestion
        return JSONResponse(error_body, status_code=exc.status_code)


@app.get("/history")
def get_history():
    history = _load_history()
    return JSONResponse({"history": history, "total": len(history)})


@app.delete("/history/{entry_id}")
def delete_history_entry(entry_id: str):
    global _USE_FILE
    history = _load_history()
    new_history = [h for h in history if h.get("id") != entry_id]
    if len(new_history) == len(history):
        raise HTTPException(status_code=404, detail="Entry not found")
    if not _USE_FILE:
        _memory_history.clear()
        _memory_history.extend(new_history)
    else:
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(new_history, f, ensure_ascii=False, indent=2)
        except Exception:
            _USE_FILE = False
            _memory_history.clear()
            _memory_history.extend(new_history)
    return JSONResponse({"deleted": True})


@app.get("/templates")
def get_templates():
    templates = [
        {
            "name": "Software Engineering Graduate",
            "description": "Fresh CS grad applying to a tech startup",
            "request": {
                "job_title": "Junior Software Engineer",
                "company_name": "TechNova Solutions",
                "job_description": (
                    "We are looking for a passionate junior software engineer to join our "
                    "team. You will work on building scalable web applications using React "
                    "and Node.js. Responsibilities include writing clean code, participating "
                    "in code reviews, and collaborating with cross-functional teams. Strong "
                    "problem-solving skills and a basic understanding of databases (PostgreSQL) "
                    "are required. Fresh graduates are welcome."
                ),
                "candidate_background": (
                    "Recent BSCS graduate from FAST-NUCES Islamabad with a GPA of 3.6. "
                    "Completed a final year project building a real-time collaboration tool "
                    "using React and Socket.io. Interned at a local startup for 2 months where "
                    "I built REST APIs using Express.js. Familiar with PostgreSQL and MongoDB. "
                    "Active GitHub profile with 10+ repositories."
                ),
                "tone": "confident",
                "word_limit": 300,
                "language": "English",
            },
        },
        {
            "name": "Marketing Manager",
            "description": "Mid-level marketer applying for a brand role",
            "request": {
                "job_title": "Brand Marketing Manager",
                "company_name": "Sapphire Retail",
                "job_description": (
                    "Sapphire is hiring a Brand Marketing Manager to lead our digital and "
                    "offline campaigns. You will manage campaign strategy, oversee agency "
                    "relationships, analyze campaign performance, and collaborate with the "
                    "creative team. 3-5 years of experience in FMCG or retail marketing "
                    "required. Proficiency in Google Analytics and Meta Ads Manager is a plus."
                ),
                "candidate_background": (
                    "4 years of marketing experience, currently at Khaadi as a Digital "
                    "Marketing Executive. Managed a monthly ad budget of PKR 3 million across "
                    "Meta and Google Ads. Led a seasonal campaign that increased online sales "
                    "by 35% YoY. Experienced with Google Analytics, Meta Business Suite, and "
                    "basic graphic design in Canva. MBA from IBA Karachi."
                ),
                "tone": "formal",
                "word_limit": 280,
                "language": "English",
            },
        },
        {
            "name": "Urdu Cover Letter – Accounting",
            "description": "Accounts officer role, letter in Urdu",
            "request": {
                "job_title": "Accounts Officer",
                "company_name": "Packages Limited",
                "job_description": (
                    "Packages Limited requires an Accounts Officer to handle day-to-day "
                    "bookkeeping, prepare financial statements, manage vendor payments, and "
                    "assist in month-end closing. Candidates must have knowledge of ERP "
                    "systems (SAP preferred) and be ACCA part-qualified or B.Com graduate."
                ),
                "candidate_background": (
                    "B.Com graduate from University of Punjab with 2 years of experience at "
                    "a textile firm handling accounts payable/receivable. Worked with QuickBooks "
                    "and basic SAP modules. Completed ACCA F1-F3. Detail-oriented and reliable "
                    "with strong Excel skills."
                ),
                "tone": "formal",
                "word_limit": 250,
                "language": "Urdu",
            },
        },
    ]
    return JSONResponse({"templates": templates})


# ── Serve index.html with no-cache headers (fixes browser cache issues) ──────
_FRONTEND_DIRS = ["public", "frontend"]

def _find_index() -> Path | None:
    for d in _FRONTEND_DIRS:
        p = Path(d) / "index.html"
        if p.exists():
            return p
    return None

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve index.html with no-cache headers so theme toggle is always fresh."""
    index_path = _find_index()
    if index_path is None:
        return HTMLResponse("<h1>Frontend not found</h1>", status_code=404)
    content = index_path.read_text(encoding="utf-8")
    return HTMLResponse(
        content=content,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


# Mount static assets — only if the directory actually exists (safe for Vercel)
def _mount_static() -> None:
    for static_dir in _FRONTEND_DIRS:
        p = Path(static_dir)
        if p.exists() and any(p.iterdir()):
            try:
                app.mount("/static", StaticFiles(directory=static_dir), name="frontend-assets")
            except Exception:
                pass
            return

_mount_static()
