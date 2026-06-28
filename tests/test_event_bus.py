import pytest
from src.event_bus.event import Event
from src.event_bus.event_bus import EventBus
from src.event_bus.base_service import BaseService


# ── Implementação concreta para testes ──────────────────────────────────────

class MockService(BaseService):
    """Serviço fictício usado apenas nos testes."""

    def __init__(self, name: str, bus: EventBus) -> None:
        super().__init__(name, bus)
        self.received_events: list[Event] = []

    def handle(self, event: Event) -> None:
        """Armazena o evento recebido para verificação no teste."""
        self.received_events.append(event)


# ── Testes da classe Event ───────────────────────────────────────────────────

class TestEvent:

    def test_event_cria_com_nome_e_payload(self):
        event = Event("news.fetched", {"title": "Notícia teste"})
        assert event.name == "news.fetched"
        assert event.payload == {"title": "Notícia teste"}

    def test_event_timestamp_gerado_automaticamente(self):
        event = Event("news.fetched", {})
        assert event.timestamp is not None
        assert "T" in event.timestamp

    def test_event_to_dict_retorna_estrutura_correta(self):
        event = Event("news.fetched", {"source": "newsapi"})
        resultado = event.to_dict()
        assert resultado["event"] == "news.fetched"
        assert resultado["payload"] == {"source": "newsapi"}
        assert "timestamp" in resultado

    def test_event_repr(self):
        event = Event("news.fetched", {})
        assert "news.fetched" in repr(event)


# ── Testes da classe BaseService ─────────────────────────────────────────────

class TestBaseService:

    def setup_method(self):
        self.bus = EventBus()

    def test_service_inicializa_com_nome_e_bus(self):
        service = MockService("FetcherService", self.bus)
        assert service.name == "FetcherService"
        assert service.bus is self.bus

    def test_service_publica_evento_via_bus(self):
        service_a = MockService("ServiceA", self.bus)
        service_b = MockService("ServiceB", self.bus)

        service_b.subscribe("news.fetched", service_b.handle)
        service_a.publish(Event("news.fetched", {"title": "Teste"}))

        assert len(service_b.received_events) == 1

    def test_base_service_e_abstrata(self):
        """BaseService não pode ser instanciada diretamente."""
        with pytest.raises(TypeError):
            BaseService("test", self.bus)


# ── Testes da classe EventBus ────────────────────────────────────────────────

class TestEventBus:

    def setup_method(self):
        """Cria um EventBus limpo antes de cada teste."""
        self.bus = EventBus()

    def test_subscriber_recebe_evento_publicado(self):
        service = MockService("TestService", self.bus)
        self.bus.subscribe("news.fetched", service.handle)

        evento = Event("news.fetched", {"title": "Teste"})
        self.bus.publish(evento)

        assert len(service.received_events) == 1
        assert service.received_events[0].name == "news.fetched"

    def test_multiplos_subscribers_recebem_mesmo_evento(self):
        service_a = MockService("ServiceA", self.bus)
        service_b = MockService("ServiceB", self.bus)

        self.bus.subscribe("news.fetched", service_a.handle)
        self.bus.subscribe("news.fetched", service_b.handle)

        self.bus.publish(Event("news.fetched", {}))

        assert len(service_a.received_events) == 1
        assert len(service_b.received_events) == 1

    def test_subscriber_nao_recebe_evento_diferente(self):
        service = MockService("TestService", self.bus)
        self.bus.subscribe("news.fetched", service.handle)

        self.bus.publish(Event("news.parsed", {}))

        assert len(service.received_events) == 0

    def test_historico_registra_eventos_publicados(self):
        self.bus.publish(Event("news.fetched", {}))
        self.bus.publish(Event("news.parsed", {}))

        historico = self.bus.get_history()
        assert len(historico) == 2
        assert historico[0].name == "news.fetched"
        assert historico[1].name == "news.parsed"

    def test_clear_history_limpa_historico(self):
        self.bus.publish(Event("news.fetched", {}))
        self.bus.clear_history()

        assert len(self.bus.get_history()) == 0

    def test_publicar_sem_subscribers_nao_lanca_erro(self):
        """Publicar evento sem ninguém inscrito não deve quebrar o sistema."""
        try:
            self.bus.publish(Event("news.fetched", {}))
        except Exception as e:
            pytest.fail(f"Publicar sem subscribers lançou erro: {e}")