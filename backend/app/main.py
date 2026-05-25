from __future__ import annotations

from contextlib import asynccontextmanager

from aiogram import Bot
from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request

from app.config import get_settings
from app.crawler.runner import crawl_active_sources
from app.db.session import SessionLocal
from app.logging import configure_logging, get_logger
from app.notifier.bot import dp
from app.notifier.telegram import send_digest
from app.pipeline.processor import process_new
from app.scheduler import build_scheduler

log = get_logger(__name__)
settings = get_settings()
bot = Bot(token=settings.telegram_bot_token)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    if settings.telegram_webhook_url:
        await bot.set_webhook(
            settings.telegram_webhook_url,
            secret_token=settings.telegram_webhook_secret or None,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"],
        )
        log.info("webhook.set", url=settings.telegram_webhook_url)
    scheduler = build_scheduler()
    scheduler.start()
    log.info("scheduler.started", jobs=[j.id for j in scheduler.get_jobs()])
    yield
    scheduler.shutdown(wait=False)
    await bot.session.close()


app = FastAPI(lifespan=lifespan)


def _check_internal(token: str | None) -> None:
    if not settings.internal_api_token or token != settings.internal_api_token:
        raise HTTPException(status_code=403, detail="forbidden")


@app.get("/health")
async def health() -> dict:
    return {"ok": True}


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    secret = settings.telegram_webhook_secret
    if secret and x_telegram_bot_api_secret_token != secret:
        raise HTTPException(status_code=403, detail="bad secret")
    data = await request.json()
    await dp.feed_update(bot, Update.model_validate(data, context={"bot": bot}))
    return {"ok": True}


@app.post("/internal/crawl")
async def internal_crawl(x_internal_token: str | None = Header(default=None)) -> dict:
    _check_internal(x_internal_token)
    async with SessionLocal() as session:
        jobs = await crawl_active_sources(session)
    return {"jobs": len(jobs), "new": sum(j.items_new for j in jobs)}


@app.post("/internal/process")
async def internal_process(x_internal_token: str | None = Header(default=None)) -> dict:
    _check_internal(x_internal_token)
    async with SessionLocal() as session:
        created = await process_new(session)
    return {"created": created}


@app.post("/internal/digest")
async def internal_digest(x_internal_token: str | None = Header(default=None)) -> dict:
    _check_internal(x_internal_token)
    async with SessionLocal() as session:
        sent = await send_digest(session)
    return {"sent": sent}
