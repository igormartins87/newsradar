from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from src.event_bus.base_service import BaseService
from src.event_bus.event import Event
from src.event_bus.event_bus import EventBus

console = Console()


class DashboardService(BaseService):
    """
    Serviço responsável por exibir o digest de notícias no terminal.

    Consome news.scored e exibe as notícias formatadas
    com cores e tabela usando a biblioteca Rich.
    """

    def __init__(self, bus: EventBus, top_n: int = 10) -> None:
        super().__init__("DashboardService", bus)
        self.top_n = top_n
        self.subscribe("news.scored", self.handle)

    def handle(self, event: Event) -> None:
        articles = event.payload.get("articles", [])
        top = articles[:self.top_n]
        self._render(top)

    def _render(self, articles: list[dict]) -> None:
        """
        Renderiza o digest no terminal usando Rich.

        Args:
            articles: Lista de artigos pontuados e ordenados
        """
        console.print()
        console.print(Panel.fit(
            "📡 [bold cyan]NewsRadar[/bold cyan] — Digest do dia",
            border_style="cyan"
        ))

        if not articles:
            console.print("[yellow]Nenhuma notícia encontrada.[/yellow]")
            return

        table = Table(
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
            border_style="dim",
            expand=True,
        )

        table.add_column("Score", justify="center", width=7)
        table.add_column("Fonte", justify="center", width=10)
        table.add_column("Título", justify="left")
        table.add_column("Tópicos", justify="left", width=20)

        for article in articles:
            score = article.get("score", 0)
            score_color = (
                "green" if score >= 8.0
                else "yellow" if score >= 6.0
                else "red"
            )
            topics = ", ".join(article.get("matched_topics", [])) or "—"

            table.add_row(
                f"[{score_color}]{score}[/{score_color}]",
                article.get("source_name", "—"),
                article.get("title", "—"),
                topics,
            )

        console.print(table)
        console.print(
            f"[dim]Total: {len(articles)} notícias exibidas[/dim]\n"
        )