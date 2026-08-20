from fastapi import APIRouter, Depends, HTTPException, Query
from src.api.cache import InMemoryCache
from src.api.rss_parser import RSSParser
from src.api.security import validate_api_key
from src.event_bus.event import Event
from src.event_bus.event_bus import EventBus
from src.score.scorer_service import ScorerService

router = APIRouter(prefix="/news", tags=["Notícias"])
rss = RSSParser()
cache = InMemoryCache(ttl=1800)


def _score_articles(articles: list[dict]) -> list[dict]:
    if not articles:
        return []
    bus = EventBus()
    scored_articles = []
    ScorerService(
        bus=bus,
        topics=[
            "inteligência artificial", "concurso", "python",
            "tecnologia", "ibge", "cesgranrio", "engenharia", "software",
            "artificial intelligence", "space", "science", "nasa",
            "machine learning", "robotics", "quantum",
        ]
    )
    def capture(event):
        scored_articles.extend(event.payload.get("articles", []))
    bus.subscribe("news.scored", capture)
    bus.publish(Event("news.parsed", {
        "source": "api",
        "total": len(articles),
        "articles": articles,
    }))
    return scored_articles if scored_articles else articles


def _fetch_and_score(source: str | None = None, limit: int = 15) -> list[dict]:
    cache_key = f"news:{source or 'all'}:{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    articles = rss.fetch(source=source, limit=limit) if source else rss.fetch_all(limit=limit)
    scored = _score_articles(articles)
    cache.set(cache_key, scored)
    return scored


@router.get("/", summary="Buscar notícias de todas as fontes")
async def get_all_news(
    limit: int = Query(default=10, ge=1, le=50),
    _: str = Depends(validate_api_key),
):
    articles = _fetch_and_score(limit=limit)
    return {"status": "ok", "total": len(articles), "articles": articles}


@router.get("/public", summary="Rota pública para o dashboard web")
async def get_public_news(
    limit: int = Query(default=15, ge=1, le=30),
):
    articles = _fetch_and_score(limit=limit)
    return {"status": "ok", "articles": articles}


@router.get("/sources", summary="Lista todas as fontes e categorias")
async def get_sources():
    return {
        "status": "ok",
        "sources": list(rss.FEEDS.keys()),
        "categories": list(rss.CATEGORIES.keys()),
    }


@router.get("/category/{category}", summary="Buscar notícias por categoria")
async def get_news_by_category(
    category: str,
    limit: int = Query(default=10, ge=1, le=30),
):
    categories_disponiveis = list(rss.CATEGORIES.keys())
    if category not in categories_disponiveis:
        raise HTTPException(
            status_code=404,
            detail=f"Categoria '{category}' não encontrada. "
                   f"Disponíveis: {categories_disponiveis}",
        )
    articles = rss.fetch_by_category(category=category, limit=limit)
    scored = _score_articles(articles)
    cache.set(f"category:{category}:{limit}", scored)
    return {"status": "ok", "category": category, "total": len(scored), "articles": scored}


@router.get("/cache/info", summary="Informações sobre o cache")
async def get_cache_info(_: str = Depends(validate_api_key)):
    return cache.info()


@router.get("/cache/clear", summary="Limpa o cache manualmente")
async def clear_cache(_: str = Depends(validate_api_key)):
    cache.clear()
    return {"status": "ok", "message": "Cache limpo com sucesso."}


@router.get("/{source}", summary="Buscar notícias de uma fonte específica")
async def get_news_by_source(
    source: str,
    limit: int = Query(default=10, ge=1, le=50),
    _: str = Depends(validate_api_key),
):
    sources_disponiveis = list(rss.FEEDS.keys())
    if source not in sources_disponiveis:
        raise HTTPException(
            status_code=404,
            detail=f"Fonte '{source}' não encontrada. "
                   f"Disponíveis: {sources_disponiveis}",
        )
    articles = _fetch_and_score(source=source, limit=limit)
    return {"status": "ok", "source": source, "total": len(articles), "articles": articles}