# 📋 Contratos de Evento — NewsRadar

> Este documento define o **payload** (conteúdo) de cada evento que trafega pelo Event Bus.
> Todo serviço que publicar ou consumir um evento **deve** seguir este contrato.

---

## O que é um contrato de evento?

Em uma arquitetura SOA orientada a eventos, os serviços se comunicam por meio de mensagens.
Um **contrato de evento** define:

- **Nome do evento** — identificador único (ex: `news.fetched`)
- **Publicador** — qual serviço envia o evento
- **Consumidores** — quais serviços escutam o evento
- **Payload** — estrutura exata dos dados enviados (campos, tipos, obrigatoriedade)

---

## Índice de eventos

| Evento | Publicador | Consumidores |
|---|---|---|
| [`news.fetched`](#1-newsfetched) | Fetcher Service | Parser Service |
| [`news.parsed`](#2-newsparsed) | Parser Service | Scorer Service |
| [`news.scored`](#3-newsscored) | Scorer Service | Notifier Service, Dashboard Service |
| [`news.alert`](#4-newsalert) | Notifier Service | — (saída final) |

---

## 1. news.fetched

**Descrição:** Publicado pelo Fetcher Service após buscar notícias brutas na API externa.
O Parser Service escuta este evento para iniciar a normalização dos dados.

**Publicador:** `Fetcher Service`
**Consumidor:** `Parser Service`

### Payload

```json
{
  "event": "news.fetched",
  "timestamp": "2024-01-15T08:30:00Z",
  "source": "newsapi",
  "articles": [
    {
      "id": "a1b2c3d4",
      "title": "OpenAI lança novo modelo com raciocínio avançado",
      "description": "A empresa anunciou hoje...",
      "url": "https://exemplo.com/noticia",
      "published_at": "2024-01-15T07:00:00Z",
      "source_name": "TechNews"
    }
  ]
}
```

### Descrição dos campos

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `event` | string | ✅ sim | Nome do evento. Sempre `"news.fetched"` |
| `timestamp` | string (ISO 8601) | ✅ sim | Data e hora em que o evento foi publicado |
| `source` | string | ✅ sim | Identificador da API de origem |
| `articles` | array | ✅ sim | Lista de artigos brutos retornados pela API |
| `articles[].id` | string | ✅ sim | Identificador único do artigo (hash) |
| `articles[].title` | string | ✅ sim | Título original do artigo |
| `articles[].description` | string | ❌ não | Resumo do artigo (pode vir vazio) |
| `articles[].url` | string | ✅ sim | URL original da notícia |
| `articles[].published_at` | string (ISO 8601) | ✅ sim | Data de publicação da notícia |
| `articles[].source_name` | string | ✅ sim | Nome do veículo de comunicação |

---

## 2. news.parsed

**Descrição:** Publicado pelo Parser Service após normalizar e limpar os dados brutos.
Duplicatas são removidas e todos os campos seguem o formato padrão do sistema.

**Publicador:** `Parser Service`
**Consumidor:** `Scorer Service`

### Payload

```json
{
  "event": "news.parsed",
  "timestamp": "2024-01-15T08:30:05Z",
  "total": 2,
  "articles": [
    {
      "id": "a1b2c3d4",
      "title": "OpenAI lança novo modelo com raciocínio avançado",
      "description": "A empresa anunciou hoje um novo modelo capaz de...",
      "url": "https://exemplo.com/noticia",
      "published_at": "2024-01-15T07:00:00Z",
      "source_name": "TechNews",
      "keywords": ["openai", "inteligência artificial", "modelo"]
    }
  ]
}
```

### Descrição dos campos

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `event` | string | ✅ sim | Nome do evento. Sempre `"news.parsed"` |
| `timestamp` | string (ISO 8601) | ✅ sim | Data e hora em que o evento foi publicado |
| `total` | integer | ✅ sim | Quantidade de artigos após limpeza |
| `articles` | array | ✅ sim | Lista de artigos normalizados |
| `articles[].keywords` | array de strings | ✅ sim | Palavras-chave extraídas do título e descrição |

> Os demais campos são idênticos ao evento `news.fetched`.

---

## 3. news.scored

**Descrição:** Publicado pelo Scorer Service após calcular a pontuação de relevância de cada artigo.
A pontuação vai de `0.0` (irrelevante) a `10.0` (máxima relevância).

**Publicador:** `Scorer Service`
**Consumidores:** `Notifier Service`, `Dashboard Service`

### Payload

```json
{
  "event": "news.scored",
  "timestamp": "2024-01-15T08:30:10Z",
  "total": 2,
  "articles": [
    {
      "id": "a1b2c3d4",
      "title": "OpenAI lança novo modelo com raciocínio avançado",
      "description": "A empresa anunciou hoje um novo modelo capaz de...",
      "url": "https://exemplo.com/noticia",
      "published_at": "2024-01-15T07:00:00Z",
      "source_name": "TechNews",
      "keywords": ["openai", "inteligência artificial", "modelo"],
      "score": 9.2,
      "matched_topics": ["inteligência artificial"]
    }
  ]
}
```

### Descrição dos campos

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `event` | string | ✅ sim | Nome do evento. Sempre `"news.scored"` |
| `timestamp` | string (ISO 8601) | ✅ sim | Data e hora em que o evento foi publicado |
| `total` | integer | ✅ sim | Quantidade de artigos pontuados |
| `articles[].score` | float (0.0 – 10.0) | ✅ sim | Pontuação de relevância calculada pelo Scorer |
| `articles[].matched_topics` | array de strings | ✅ sim | Tópicos de interesse que geraram a pontuação |

---

## 4. news.alert

**Descrição:** Publicado pelo Notifier Service quando um artigo ultrapassa o limiar de pontuação
configurado (padrão: `score >= 8.0`). Representa uma notícia de alta relevância.

**Publicador:** `Notifier Service`
**Consumidor:** saída final (terminal / futuro: e-mail, Telegram)

### Payload

```json
{
  "event": "news.alert",
  "timestamp": "2024-01-15T08:30:12Z",
  "alert_level": "high",
  "article": {
    "id": "a1b2c3d4",
    "title": "OpenAI lança novo modelo com raciocínio avançado",
    "url": "https://exemplo.com/noticia",
    "score": 9.2,
    "matched_topics": ["inteligência artificial"]
  }
}
```

### Descrição dos campos

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `event` | string | ✅ sim | Nome do evento. Sempre `"news.alert"` |
| `timestamp` | string (ISO 8601) | ✅ sim | Data e hora em que o alerta foi gerado |
| `alert_level` | string | ✅ sim | Nível do alerta: `"high"` (score ≥ 8.0) ou `"medium"` (score ≥ 6.0) |
| `article` | object | ✅ sim | Artigo que gerou o alerta (campos essenciais) |

---

## Regras gerais dos contratos

1. **Todo evento deve ter os campos `event` e `timestamp`** — são obrigatórios em qualquer mensagem.
2. **O campo `event` é imutável** — nunca mude o nome de um evento sem atualizar todos os consumidores.
3. **Campos novos são adicionados, nunca removidos** — isso garante compatibilidade com versões anteriores.
4. **Datas sempre no formato ISO 8601** — ex: `2024-01-15T08:30:00Z`.
5. **IDs de artigos são gerados como hash do título + URL** — evita duplicatas entre execuções.

---

## Histórico de versões dos contratos

| Versão | Data | Alteração |
|---|---|---|
| v1.0 | 2024-01-15 | Criação inicial dos contratos |
