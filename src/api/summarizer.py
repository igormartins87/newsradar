import os
import logging
from groq import Groq

logger = logging.getLogger(__name__)


class AISummarizer:
    """
    Serviço de sumarização de notícias em inglês usando Groq.
    Só processa artigos com language='en'.
    """

    MODEL = "openai/gpt-oss-20b"

    def __init__(self) -> None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY não encontrada no .env")
        self.client = Groq(api_key=api_key)

    def summarize(self, title: str, description: str) -> str | None:
        if not title:
            return None

        prompt = f"""Resuma a notícia abaixo em português brasileiro em 2 frases curtas.
Vá direto ao ponto sem introduções.

Título: {title}
Descrição: {description or ''}

Resumo:"""

        try:
            response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.3,
            )
            content = response.choices[0].message.content
            logger.info(f"[AISummarizer] content raw: {repr(content)}")

            if not content:
                return None

            summary = content.strip()

            if not summary:
                return None

            logger.info(f"[AISummarizer] Resumo gerado: {title[:50]}...")
            return summary
        except Exception as e:
            logger.error(f"[AISummarizer] Erro ao sumarizar: {e}")
            return None

    def summarize_batch(self, articles: list[dict]) -> list[dict]:
        result = []
        en_count = 0

        for article in articles:
            if article.get("language") == "en":
                summary = self.summarize(
                    title=article.get("title", ""),
                    description=article.get("description", ""),
                )
                logger.info(f"[AISummarizer] summary value: {repr(summary)}")
                if summary:
                    article["ai_summary"] = summary
                    article["has_ai_summary"] = True
                    en_count += 1
                else:
                    article["has_ai_summary"] = False
            else:
                article["has_ai_summary"] = False

            result.append(article)

        logger.info(f"[AISummarizer] {en_count} artigos sumarizados.")
        return result