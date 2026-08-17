import httpx
from src.event_bus.event import Event
from src.event_bus.event_bus import EventBus
from src.event_bus.base_service import BaseService


class FetcherService(BaseService):
    """
    Serviço responsável por buscar notícias na NewsRadar API.

    É o único serviço que se comunica com o mundo externo.
    Após buscar, publica o evento news.fetched no EventBus
    para que o ParserService processe os dados.
    """

    API_URL = "https://newsradar-api-s8id.onrender.com"

    def __init__(self, bus: EventBus, api_key: str) -> None:
        super().__init__("FetcherService", bus)
        self.api_key = api_key
        self.headers = {"X-API-Key": api_key}

    def fetch(self, source: str = None, limit: int = 10) -> None:
        """
        Busca notícias na API e publica evento news.fetched.

        Args:
            source: fonte específica (g1, bbc, tecmundo) ou None para todas
            limit: quantidade de notícias por fonte
        """
        url = (
            f"{self.API_URL}/news/{source}"
            if source
            else f"{self.API_URL}/news/?limit={limit}"
        )

        print(f"[{self.name}] Buscando notícias em: {url}")

        try:
            response = httpx.get(url, headers=self.headers, timeout=60)
            response.raise_for_status()
            data = response.json()

            articles = data.get("articles", [])
            print(f"[{self.name}] {len(articles)} notícias encontradas.")

            evento = Event("news.fetched", {
                "source": source or "all",
                "articles": articles,
            })

            self.publish(evento)

        except httpx.TimeoutException:
            print(f"[{self.name}] Timeout ao chamar a API.")
        except httpx.HTTPStatusError as e:
            print(f"[{self.name}] Erro HTTP: {e.response.status_code}")
        except Exception as e:
            print(f"[{self.name}] Erro inesperado: {e}")

    def handle(self, event: Event) -> None:
        """FetcherService não consome eventos — só publica."""
        pass