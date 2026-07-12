from fastapi import APIRouter, Depends, Query
from src.api.security import validate_api_key
from src.api.rss_parser import RSSParser

router = APIRouter(prefix="/news", tags=["Notícias"])
rss = RSSParser()


@router.get(
    "/",
    summary="Buscar notícias de todas as fontes",
    description="Retorna notícias agregadas de G1, BBC e Tecmundo via RSS.",
)
async def get_all_news(
    limit: int = Query(default=10, ge=1, le=50,
                       description="Quantidade de notícias por fonte"),
    _: str = Depends(validate_api_key),
):
    return {
        "status": "ok",
        "total": 0,
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
        from fastapi import HTTPException
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