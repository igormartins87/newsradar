from abc import ABC, abstractmethod
from .event import Event
from .event_bus import EventBus



class BaseService(ABC):
    """
    Classe base abstrata para todos os serviços do NewsRadar.
 
    Define o contrato que todo serviço deve cumprir:
    - Ter um nome único
    - Ter acesso ao EventBus
    - Implementar o método handle() para processar eventos recebidos
 
    Todos os serviços (Fetcher, Parser, Scorer, etc.) herdam desta classe,
    garantindo consistência e reuso de código — princípios de POO e SOA.
    """
 
    def __init__(self, name: str, bus: EventBus) -> None:
        """
        Inicializa o serviço base.
 
        Args:
            name: Nome único do serviço (ex: 'FetcherService')
            bus: Instância do EventBus compartilhado
        """
        self.name = name
        self.bus = bus
        print(f"[{self.name}] Serviço iniciado.")
 
    def publish(self, event: Event) -> None:
        """
        Publica um evento no barramento.
 
        Args:
            event: Evento a ser publicado
        """
        self.bus.publish(event)
 
    def subscribe(self, event_name: str, callback) -> None:
        """
        Inscreve o serviço para escutar um tipo de evento.
 
        Args:
            event_name: Nome do evento para escutar
            callback: Método que será chamado ao receber o evento
        """
        self.bus.subscribe(event_name, callback)
 
    @abstractmethod
    def handle(self, event: Event) -> None:
        """
        Processa um evento recebido do barramento.
 
        Método abstrato — cada serviço implementa sua própria
        lógica de processamento.
 
        Args:
            event: Evento recebido para processar
        """
        pass
 
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
