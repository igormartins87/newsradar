import os
from dotenv import load_dotenv
from src.event_bus.event_bus import EventBus
from src.fetcher.fetcher_service import FetcherService
from src.parser.parser_service import ParserService
from src.score.scorer_service import ScorerService
from src.notifier.notifier_service import NotifierService
from src.dashboard.dashboard_service import DashboardService

load_dotenv()


def main() -> None:
    """
    Orquestra todos os serviços do NewsRadar.

    Inicializa o EventBus compartilhado, registra todos
    os serviços e dispara o fluxo de busca de notícias.
    """
    print("\n🚀 Iniciando NewsRadar...\n")

    # Barramento compartilhado entre todos os serviços
    bus = EventBus()

    # Inicializar serviços — a ordem importa!
    # Os consumidores devem se inscrever antes do Fetcher publicar
    ParserService(bus=bus)
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
        ]
    )
    NotifierService(bus=bus, threshold=6.0)
    DashboardService(bus=bus, top_n=10)

    # Fetcher é o último a ser iniciado — dispara o fluxo
    fetcher = FetcherService(
        bus=bus,
        api_key=os.getenv("API_KEY", "newsradar-chave-secreta-2024")
    )

    # Buscar de todas as fontes
    print("\n📡 Buscando notícias...\n")
    fetcher.fetch(limit=10)

    print("\n✅ NewsRadar finalizado!\n")


if __name__ == "__main__":
    main()