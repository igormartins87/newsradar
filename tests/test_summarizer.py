from unittest.mock import patch, MagicMock
from src.api.summarizer import AISummarizer


class TestAISummarizer:

    def setup_method(self):
        with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}):
            self.summarizer = AISummarizer()

    # ── Inicialização ────────────────────────────────────────────────────

    def test_inicializa_com_api_key(self):
        with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}):
            s = AISummarizer()
            assert s.client is not None

    def test_inicializa_sem_api_key_lanca_erro(self):
        import pytest
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="GROQ_API_KEY"):
                AISummarizer()

    def test_model_configurado(self):
        assert self.summarizer.MODEL is not None
        assert len(self.summarizer.MODEL) > 0

    # ── Método summarize ─────────────────────────────────────────────────

    @patch("groq.Groq")
    def test_summarize_retorna_resumo(self, mock_groq_class):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(
                message=MagicMock(content="Resumo gerado pela IA em português.")
            )]
        )
        self.summarizer.client = mock_client

        result = self.summarizer.summarize(
            title="NASA discovers new planet",
            description="Scientists found a new exoplanet"
        )

        assert result == "Resumo gerado pela IA em português."
        assert mock_client.chat.completions.create.called

    @patch("groq.Groq")
    def test_summarize_titulo_vazio_retorna_none(self, mock_groq):
        result = self.summarizer.summarize(title="", description="qualquer coisa")
        assert result is None

    @patch("groq.Groq")
    def test_summarize_erro_api_retorna_none(self, mock_groq):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        self.summarizer.client = mock_client

        result = self.summarizer.summarize(
            title="NASA discovers new planet",
            description="Description"
        )
        assert result is None

    @patch("groq.Groq")
    def test_summarize_conteudo_vazio_retorna_none(self, mock_groq):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=""))]
        )
        self.summarizer.client = mock_client

        result = self.summarizer.summarize(
            title="NASA discovers new planet",
            description="Description"
        )
        assert result is None

    # ── Método summarize_batch ───────────────────────────────────────────

    def test_summarize_batch_processa_apenas_en(self):
        with patch.object(self.summarizer, "summarize", return_value="Resumo") as mock_sum:
            articles = [
                {"title": "Notícia PT", "description": "", "language": "pt"},
                {"title": "EN News", "description": "", "language": "en"},
            ]
            result = self.summarizer.summarize_batch(articles)

            assert mock_sum.call_count == 1
            assert result[0]["has_ai_summary"] is False
            assert result[1]["has_ai_summary"] is True
            assert result[1]["ai_summary"] == "Resumo"

    def test_summarize_batch_pt_nao_tem_ai_summary(self):
        articles = [
            {"title": "Notícia PT", "description": "", "language": "pt"},
        ]
        result = self.summarizer.summarize_batch(articles)
        assert result[0]["has_ai_summary"] is False
        assert "ai_summary" not in result[0]

    def test_summarize_batch_lista_vazia(self):
        result = self.summarizer.summarize_batch([])
        assert result == []

    def test_summarize_batch_preserva_campos_originais(self):
        with patch.object(self.summarizer, "summarize", return_value="Resumo"):
            articles = [
                {
                    "title": "EN News",
                    "description": "Desc",
                    "language": "en",
                    "score": 8.5,
                    "source_name": "TECHCRUNCH",
                }
            ]
            result = self.summarizer.summarize_batch(articles)
            assert result[0]["score"] == 8.5
            assert result[0]["source_name"] == "TECHCRUNCH"
            assert result[0]["title"] == "EN News"

    def test_summarize_batch_resumo_falha_has_ai_summary_false(self):
        with patch.object(self.summarizer, "summarize", return_value=None):
            articles = [
                {"title": "EN News", "description": "", "language": "en"},
            ]
            result = self.summarizer.summarize_batch(articles)
            assert result[0]["has_ai_summary"] is False