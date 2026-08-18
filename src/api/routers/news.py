from fastapi import APIRouter, Depends, HTTPException, Query
from src.api.rss_parser import RSSParser
from src.api.security import validate_api_key
from src.event_bus.event_bus import EventBus
from src.score.scorer_service import ScorerService

router = APIRouter(prefix="/news", tags=["Notícias"])
rss = RSSParser()


def _score_articles(articles: list[dict]) -> list[dict]:
    """
    Pontua os artigos usando o ScorerService.

    Cria um EventBus temporário, publica os artigos
    e captura o resultado pontuado.
    """
    if not articles:
        return []

    bus = EventBus()
    scored_articles = []

    ScorerService(
        bus=bus,
        topics=[
            "inteligência artificial",
            "concurso",
            "python",
            "tecnologia",
            "ibge",
            "cesgranrio",
            "engenharia",
            "software",
        ]
    )

    # Captura o resultado do scorer
    def capture(event):
        scored_articles.extend(event.payload.get("articles", []))

    bus.subscribe("news.scored", capture)

    from src.event_bus.event import Event
    bus.publish(Event("news.parsed", {
        "source": "api",
        "total": len(articles),
        "articles": articles,
    }))

    return scored_articles if scored_articles else articles


@router.get(
    "/",
    summary="Buscar notícias de todas as fontes",
    description="Retorna notícias agregadas de G1, BBC e Tecmundo via RSS.",
)
async def get_all_news(
    limit: int = Query(default=10, ge=1, le=50),
    _: str = Depends(validate_api_key),
):
    articles = rss.fetch_all(limit=limit)
    scored = _score_articles(articles)
    return {
        "status": "ok",
        "total": len(scored),
        "articles": scored,
    }


@router.get(
    "/public",
    summary="Rota pública para o dashboard web",
)
async def get_public_news(
    limit: int = Query(default=15, ge=1, le=30),
):
    articles = rss.fetch_all(limit=limit)
    scored = _score_articles(articles)
    return {
        "status": "ok",
        "articles": scored,
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
    scored = _score_articles(articles)
    return {
        "status": "ok",
        "source": source,
        "total": len(scored),
        "articles": scored,
    }