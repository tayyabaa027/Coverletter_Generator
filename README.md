# ✦ Cover Letter Pro

AI-powered cover letter generator built with FastAPI + Groq, deployable on Vercel.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Visit%20App-brightgreen?style=for-the-badge&logo=vercel)](https://coverletter-generator-7kgq.vercel.app)

---

## Features

- 🤖 **AI Generation** — Groq API with `llama-3.3-70b-versatile`, responses in ~0.5s
- 🎨 **Dark / Light Mode** — smooth toggle switch, preference saved locally
- 📋 **Quick Templates** — 3 pre-filled templates: Software Dev, Marketing, Urdu Accounting
- 🌐 **Multi-language** — generate in English, Urdu, French, or any language
- 🎚 **Word limit slider** — 100–800 words, precision-controlled
- 🗂 **History** — every letter saved with metadata; load or delete anytime
- ⬇️ **Copy & Save** — one-click copy or download as `.txt`
- 🛡 **Rate limiting** — 10 requests/min per IP to protect your quota
- ☁️ **Vercel-ready** — serverless deployment out of the box

---

## Quick Start

**1. Install dependencies**

```bash
pip install -r requirements.txt
```

**2. Set your Groq API key**

Get a free key at [console.groq.com/keys](https://console.groq.com/keys), then:

```bash
cp .env.example .env
```

Open `.env` and add your key:

```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
```

**3. Run the server**

```bash
uvicorn app.main:app --reload
python -m uvicorn app.main:app --reload
```

Open http://localhost:8000 — you're live.

---

## Deploy to Vercel

```bash
npm i -g vercel
vercel
```

Add `GROQ_API_KEY` in the Vercel dashboard under Environment Variables. The `vercel.json` handles everything else.

---

## Project Structure

```
coverletter-pro/
├── api/
│   └── index.py          # Vercel serverless entry point
├── app/
│   ├── main.py           # FastAPI routes & history logic
│   ├── llm_client.py     # Groq API wrapper
│   ├── prompts.py        # System & user prompt builders
│   └── schemas.py        # Pydantic models
├── public/
│   └── index.html        # Frontend (HTML + CSS + JS)
├── .env.example
├── requirements.txt
├── vercel.json
└── README.md
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/generate` | Generate a cover letter |
| GET | `/history` | List all saved letters |
| DELETE | `/history/{id}` | Delete a history entry |
| GET | `/templates` | Get quick-fill templates |
| GET | `/debug/verify-key` | Test Groq API connectivity |
| GET | `/health` | Health check |

**POST `/generate` — request body**

```json
{
  "job_title": "Frontend Developer",
  "company_name": "Google",
  "job_description": "We are looking for...",
  "candidate_background": "3 years React experience...",
  "tone": "confident",
  "language": "English",
  "word_limit": 300
}
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Your Groq API key |

---

## License

MIT © 2025
