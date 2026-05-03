# 📡 NewsRadar

> Agregador de notícias orientado a eventos, construído com arquitetura SOA em Python.

![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Arquitetura](https://img.shields.io/badge/arquitetura-SOA-purple)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 📌 Sobre o projeto

O **NewsRadar** é um sistema de agregação de notícias construído com **Arquitetura Orientada a Serviços (SOA)** e movido a eventos. Ele busca notícias em APIs públicas, normaliza os dados, pontua a relevância por palavras-chave e exibe um digest formatado no terminal.

O projeto foi desenvolvido com foco em **aprendizado prático de Engenharia de Software**, cobrindo conceitos como:

- Arquitetura SOA e baixo acoplamento entre serviços
- Comunicação orientada a eventos com Event Bus
- Modelagem profissional com diagramas UML
- Boas práticas de documentação e versionamento com Git

---

## 🏗️ Arquitetura

O sistema é composto por **5 serviços independentes** que se comunicam exclusivamente por meio de um barramento de eventos central (Event Bus), sem chamadas diretas entre si.

```mermaid
graph TD
    A[Fetcher Service] -->|news.fetched| EB((Event Bus))
    EB -->|news.fetched| B[Parser Service]
    B -->|news.parsed| EB
    EB -->|news.parsed| C[Scorer Service]
    C -->|news.scored| EB
    EB -->|news.scored| D[Notifier Service]
    EB -->|news.scored| E[Dashboard Service]

    style EB fill:#F5C75A,stroke:#BA7517,color:#412402
    style A fill:#B5D4F4,stroke:#185FA5,color:#042C53
    style B fill:#CECBF6,stroke:#534AB7,color:#26215C
    style C fill:#9FE1CB,stroke:#0F6E56,color:#04342C
    style D fill:#F5C4B3,stroke:#993C1D,color:#4A1B0C
    style E fill:#C0DD97,stroke:#3B6D11,color:#173404
```

### Serviços

| Serviço | Responsabilidade | Publica | Consome |
|---|---|---|---|
| **Fetcher** | Busca notícias em APIs públicas | `news.fetched` | — |
| **Parser** | Normaliza e remove duplicatas | `news.parsed` | `news.fetched` |
| **Scorer** | Calcula relevância por palavras-chave | `news.scored` | `news.parsed` |
| **Notifier** | Gera alertas para notícias relevantes | `news.alert` | `news.scored` |
| **Dashboard** | Exibe digest formatado no terminal | — | `news.scored` |

> Diagrama completo de arquitetura em [`docs/architecture.md`](docs/architecture.md)
> Contratos de evento em [`docs/event-contracts.md`](docs/event-contracts.md)

---

## 📁 Estrutura do repositório

```
newsradar/
├── README.md                  ← este arquivo
├── CHANGELOG.md               ← histórico de versões
├── .gitignore
├── docs/
│   ├── architecture.md        ← diagrama SOA detalhado
│   ├── event-contracts.md     ← payload JSON de cada evento
│   ├── use-cases.md           ← casos de uso
│   └── diagrams/              ← arquivos .drawio e imagens
├── src/
│   ├── event_bus/             ← barramento de eventos
│   ├── fetcher/               ← serviço de busca
│   ├── parser/                ← serviço de normalização
│   ├── scorer/                ← serviço de pontuação
│   ├── notifier/              ← serviço de alertas
│   └── dashboard/             ← serviço de exibição
└── tests/                     ← testes por serviço
```

---

## 🚀 Roadmap

- [x] Modelagem da arquitetura SOA
- [x] Estrutura do repositório
- [ ] Implementação do Event Bus
- [ ] Fetcher Service (NewsAPI)
- [ ] Parser Service
- [ ] Scorer Service
- [ ] Notifier Service
- [ ] Dashboard Service (terminal com `rich`)
- [ ] Testes unitários por serviço
- [ ] Scheduler automático com `APScheduler`

---

## 🛠️ Tecnologias

| Tecnologia | Uso |
|---|---|
| Python 3.11+ | Linguagem principal |
| NewsAPI | Fonte de notícias |
| Rich | Interface no terminal |
| APScheduler | Agendamento de execução |
| Mermaid | Diagramas no Markdown |
| Draw.io | Diagramas de arquitetura |

---

## ▶️ Como executar

> Em desenvolvimento — instruções serão adicionadas na Fase 2.

```bash
# Clone o repositório
git clone https://github.com/SEU_USUARIO/newsradar.git
cd newsradar

# Crie o ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows

# Instale as dependências
pip install -r requirements.txt

# Execute
python src/main.py
```

---

## 📚 Documentação

| Documento | Descrição |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Arquitetura SOA detalhada |
| [`docs/event-contracts.md`](docs/event-contracts.md) | Contratos de evento (payload JSON) |
| [`docs/use-cases.md`](docs/use-cases.md) | Casos de uso do sistema |
| [`CHANGELOG.md`](CHANGELOG.md) | Histórico de versões |

---

## 🎯 Objetivo de aprendizado

Este projeto foi desenvolvido para estudo prático de:

- **Arquitetura SOA** — separação de responsabilidades, baixo acoplamento, reusabilidade de serviços
- **Orientação a eventos** — publish/subscribe, contratos de evento, barramento de mensagens
- **Engenharia de Software** — modelagem UML, documentação técnica, versionamento semântico
- **Boas práticas Git** — Conventional Commits, estrutura de repositório, changelog

---

## 👤 Autor

Feito por **Igor Martins** — Analista de Sistemas com foco no backend.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-conectar-blue?logo=linkedin)](https://www.linkedin.com/in/igor-martins1)
[![GitHub](https://img.shields.io/badge/GitHub-seguir-black?logo=github)](https://github.com/igormartins87)

---

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.
