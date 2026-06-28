# import pytest
from  src.event_bus.event import Event

class TestEvent:
    def test_event_cria_com_nome_e_payload(self):
        event = Event("news.fetched" , {"title": "Notícia teste"})
        assert event.name == "news.fetched"
        assert event.payload == {"title": "Notícia teste"}

    def test_event_timestamp_gerado_automaticamente(self):
        event = Event("news.fetched", {})
        assert event.timestamp is not None
        assert "T" in event.timestamp

    def test_event_to_dict_retorna_estrutura_correta(self):
        event = Event("news.fetched" , {"source": "newsapi"})
        resultado = event.to_dict()
        assert resultado ["event"] == "news.fetched"
        assert resultado ["payload"] == {"source": "newsapi"}
        assert "timestamp" in resultado

    def test_event_repr(self):
        event = Event ("news.fetched", {})
        assert "news.fetched" in repr(event)

     

