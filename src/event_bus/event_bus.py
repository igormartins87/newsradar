from collections import defaultdict
from typing import Callable
from .event import Event

class EventBus:
    """
    Barramento central de eventos do NewsRadar.
 
    Implementa o padrão Publish/Subscribe (Pub/Sub):
    - Serviços publicam eventos sem saber quem vai consumi-los
    - Serviços se inscrevem em eventos sem saber quem os publica
    - O EventBus é o único ponto de contato entre os serviços
 
    Atributos:
        _subscribers: dicionário que mapeia nome do evento → lista de callbacks
        _history: lista de todos os eventos publicados (útil para debug)
    """
 
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._history: list[Event] = []
 
    def subscribe(self, event_name: str, callback: Callable) -> None:
        """
        Inscreve um callback para ser chamado quando um evento ocorrer.
 
        Args:
            event_name: Nome do evento para escutar (ex: 'news.fetched')
            callback: Função que será chamada ao receber o evento
        """
        self._subscribers[event_name].append(callback)
        name = getattr(callback, '__self__', None)
        name = getattr(name, 'name', callback.__name__ if hasattr(callback, '__name__') else 'anonymous')
        print(f"[EventBus] '{name}' inscrito em '{event_name}'")
 
    def publish(self, event: Event) -> None:
        """
        Publica um evento no barramento e notifica todos os inscritos.
 
        Args:
            event: Instância de Event a ser publicada
        """
        self._history.append(event)
        print(f"[EventBus] Publicando evento '{event.name}'")
 
        subscribers = self._subscribers.get(event.name, [])
 
        if not subscribers:
            print(f"[EventBus] Nenhum inscrito para '{event.name}'")
            return
 
        for callback in subscribers:
            callback(event)
 
    def get_history(self) -> list[Event]:
        """
        Retorna o histórico de todos os eventos publicados.
 
        Returns:
            Lista de eventos na ordem em que foram publicados
        """
        return self._history.copy()
 
    def clear_history(self) -> None:
        """Limpa o histórico de eventos."""
        self._history.clear()
        print("[EventBus] Histórico limpo.")
 
    def __repr__(self) -> str:
        return (
            f"EventBus("
            f"subscribers={len(self._subscribers)}, "
            f"history={len(self._history)})"
        )
 
