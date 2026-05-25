# Crawler Konten Backend

Mesin editorial untuk konten storytelling (horor/misteri). Backend FastAPI + worker.
Lihat plan lengkap di `../workflow_plan_crawler_konten/` dan spec arsitektur.

## Fokus saat ini (backend-first)
Crawling → Scripting → Stress test, sebelum dashboard/audio/analytics.

## Setup lokal

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env   # lalu isi key asli (Gemini paid, Telegram, Neon, R2, Drive)
```

## Arsitektur ringkas
- **API + worker**: FastAPI + `procrastinate` (queue di Postgres, tanpa Redis)
- **DB**: Neon Postgres + `pgvector` (data terstruktur + cleaned_text + embedding)
- **Raw storage**: Cloudflare R2 (raw HTML/audio/visual)
- **LLM**: Gemini via `litellm` Flash free (enrichment/scoring) + Gemini paid (research/skrip)
- **Notifier**: Telegram grup (webhook), gate approve/reject + rewrite
- **Scheduler**: GitHub Actions cron (window collection 10:00–22:00, approval 01:00–10:00)

## Struktur
```
app/
  api/          routers FastAPI
  crawler/      adapters, fetcher, extractor, validator
  pipeline/     cleaner, dedup, enricher, scoring
  agents/       research_agent, script_pipeline
  voice/        style extraction + RAG dari corpus lesson/
  llm/          litellm wrapper + routing hybrid + safety
  notifier/     telegram bot
  integrations/ google drive, r2
  jobs/         procrastinate tasks
  db/           models + session + migrations
```
