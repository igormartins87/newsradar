import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
from src.api.routers import news

load_dotenv()

# Rate Limiter — OWASP: limitar requisições por IP
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="NewsRadar API",
    description="API de agregação de notícias via RSS — Arquitetura SOA",
    version="1.0.0",
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — OWASP: controlar origens permitidas
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["GET"],
    allow_headers=["X-API-Key"],
)

# Routers
app.include_router(news.router)


@app.get("/", tags=["Health"])
async def health_check():
    """Verifica se a API está no ar."""
    return {"status": "ok", "service": "NewsRadar API"}