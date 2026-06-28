from datetime import datetime, timezone


class Event:
    """
    Representa uma mensagem que trafega pelo Event Bus.

    Cada evento tem um nome único que identifica o tipo de mensagem
    (ex: 'news.fetched'), um payload com os dados e um timestamp
    gerado automaticamente no momento da criação.
    """

    def __init__(self, name: str, payload: dict) -> None:
        """
        Inicializa um novo evento.

        Args:
            name: Nome do evento (ex: 'news.fetched')
            payload: Dicionário com os dados do evento
        """
        self.name = name
        self.payload = payload
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        """
        Converte o evento para dicionário.

        Returns:
            Dicionário com name, payload e timestamp
        """
        return {
            "event": self.name,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }

    def __repr__(self) -> str:
        return f"Event(name='{self.name}', timestamp='{self.timestamp}')"