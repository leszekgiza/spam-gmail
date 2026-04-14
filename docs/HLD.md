# HLD — SPAM Gmail

## Architektura

```mermaid
flowchart TB
    Gmail[Gmail API]
    Neon[(Neon Postgres)]
    Vercel[Vercel Functions<br/>Fluid Compute Python 3.13]
    Gateway[Vercel AI Gateway<br/>Claude Haiku 4.5]
    Blob[Vercel Blob<br/>ML model artifacts]
    Web[Next.js Web<br/>spamgmail.vercel.app]
    User((Leszek))
    WhatsApp[WhatsApp MCP]

    subgraph Crons [Vercel Cron]
        Fetch["03:00 fetch.py"]
        Classify["06:00 classify.py"]
        Purge["06:30 purge.py"]
    end

    Fetch -->|pobierz nowe| Gmail
    Fetch -->|INSERT raw_emails| Neon

    Classify -->|SELECT new| Neon
    Classify -->|fast classify| Blob
    Classify -.->|uncertain| Gateway
    Classify -->|INSERT decisions| Neon
    Classify -->|archive to _AI_TRASH| Gmail
    Classify -->|notify| WhatsApp

    Purge -->|labels>7d| Gmail
    Purge -->|INSERT audit_log| Neon

    User --> Web
    Web -->|review/confirm/restore| Neon
    Web -->|delete/restore| Gmail
    Web -->|feedback| Neon
```

## Flow: dzień typowy (Faza 2 — ASSISTED_MODE)

```mermaid
sequenceDiagram
    participant C as Cron
    participant G as Gmail
    participant DB as Neon
    participant M as Klasyfikator
    participant W as WhatsApp
    participant U as Leszek
    participant UI as Web UI

    C->>G: 03:00 fetch new messages
    G-->>DB: raw_emails INSERT

    C->>DB: 06:00 SELECT new emails
    DB-->>M: batch
    M->>M: fast classify (sklearn)
    alt confidence < 0.7
        M->>Gateway: Haiku 4.5 (z prompt cache)
        Gateway-->>M: decision + reasoning
    end
    M-->>DB: decisions INSERT
    M->>G: archive spam → _AI_TRASH label
    M->>W: "X maili do przeglądu"

    U->>UI: otwiera spamgmail.vercel.app
    UI->>DB: SELECT today's decisions
    U->>UI: zaznacza false positives + klik "Confirm"
    UI->>G: restore zaznaczone + delete reszta
    UI->>DB: feedback INSERT (training set)
```

## Flow: Faza 1 — SHADOW_MODE (tydzień 1)

```mermaid
sequenceDiagram
    participant C as Cron
    participant G as Gmail
    participant DB as Neon
    participant M as Klasyfikator
    participant U as Leszek

    C->>G: 03:00 fetch new
    G-->>DB: raw_emails

    C->>M: 06:00 klasyfikuj
    M-->>DB: decisions INSERT (tylko prognoza)
    Note over M,G: Żadnych akcji na Gmailu!

    U->>G: ręcznie kasuje / czyta / zostawia

    C->>G: 23:00 observation sweep
    G-->>DB: observations INSERT (final_state)

    Note over DB: Niedziela: porównaj decisions vs observations<br/>→ raport precision/recall
```

## Komponenty

| Komponent | Technologia | Odpowiedzialność |
|-----------|-------------|------------------|
| **Cron fetch** | Python Vercel Function | Pobranie nowych maili z Gmail → Neon |
| **Cron classify** | Python Vercel Function | Klasyfikacja + (opc.) archiwizacja |
| **Cron purge** | Python Vercel Function | Trwałe kasowanie po 7 dniach |
| **Cron observe** | Python Vercel Function | (Shadow mode) zapisanie final_state |
| **Web UI** | Next.js App Router | Poranny przegląd + potwierdzenia |
| **Classifier** | scikit-learn | Szybka klasyfikacja na cechach |
| **LLM adapter** | Anthropic SDK + AI Gateway | Haiku 4.5 dla niepewnych |
| **Gmail wrapper** | google-api-python-client | fetch, archive, label, delete |
| **DB** | Neon Postgres | raw_emails, decisions, observations, feedback, audit_log |

## Feature flagi (Vercel Edge Config)

| Flag | Default | Opis |
|------|---------|------|
| `SHADOW_MODE` | `true` | Model tylko obserwuje, żadnych akcji |
| `AUTO_DELETE` | `false` | Auto-kasowanie bez potwierdzenia |
| `LLM_ENABLED` | `true` | Użyj Haiku dla niepewnych |
| `EMERGENCY_STOP` | `false` | Kill switch — cron exit early |
| `DRY_RUN` | `false` | Loguj decyzje ale nie wykonuj akcji |

## Model versioning

Każda decyzja zapisuje `model_version` (np. `v2025-04-14_gbm_v1`). Modele ML w Vercel Blob: `models/{version}.joblib`. Retrening tworzy nową wersję, eval harness porównuje; promocja dopiero po ≥ baseline.
