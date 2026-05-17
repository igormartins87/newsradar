```mermaid
graph TD
    EXT([APIs PúblicasNewsAPI / GNews])

    subgraph SOA["🏗️ NewsRadar — Arquitetura SOA"]
        FE[Fetcher Service]
        PA[Parser Service]
        SC[Scorer Service]
        NO[Notifier Service]
        DA[Dashboard Service]
        EB((Event Bus))
    end

    EXT -->|HTTP Request| FE
    FE -->|news.fetched| EB
    EB -->|news.fetched| PA
    PA -->|news.parsed| EB
    EB -->|news.parsed| SC
    SC -->|news.scored| EB
    EB -->|news.scored| NO
    EB -->|news.scored| DA
```