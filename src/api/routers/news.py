from fastapi import APIRouter, Depends, HTTPException, Query
from src.api.rss_parser import RSSParser
from src.api.security import validate_api_key

router = APIRouter(prefix="/news", tags=["Notícias"])
rss = RSSParser()


@router.get(
    "/",
    summary="Buscar notícias de todas as fontes",
)
async def get_all_news(
    limit: int = Query(default=10, ge=1, le=50),
    _: str = Depends(validate_api_key),
):
    return {
        "status": "ok",
        "total": 0,
        "articles": rss.fetch_all(limit=limit),
    }


@router.get(
    "/public",
    summary="Rota pública para o dashboard web",
)
async def get_public_news(
    limit: int = Query(default=15, ge=1, le=30),
):
    return {
        "status": "ok",
        "articles": rss.fetch_all(limit=limit),
    }


@router.get(
    "/{source}",
    summary="Buscar notícias de uma fonte específica",
)
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
    articles = rss.fetch(source=source, limit=limit)
    return {
        "status": "ok",
        "source": source,
        "total": len(articles),
        "articles": articles,
    }