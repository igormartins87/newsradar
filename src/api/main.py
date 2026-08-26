import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from dotenv import load_dotenv
from src.api.routers import news
from src.api.scheduler import NewsScheduler

load_dotenv()

limiter = Limiter(key_func=get_remote_address)
scheduler = NewsScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação.
    Inicia o scheduler quando a API sobe e
    para quando a API encerra.
    """
    scheduler.start()
    yield
    scheduler.stop()


app = FastAPI(
    title="NewsRadar API",
    description="API de agregação de notícias via RSS — Arquitetura SOA",
    version="2.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Adiciona headers de segurança em todas as respostas."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


app.include_router(news.router)


@app.get("/", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "service": "NewsRadar API",
        "version": "2.0.0",
        "scheduler": "running",
    }