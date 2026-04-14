# SPAM Gmail — AI Inbox Cleaner

Autonomiczny system AI, który codziennie o 6:00 czyści skrzynkę Gmail ucząc się na Twoich decyzjach (co kasujesz, co zostawiasz, co czytasz).

## Jak to działa

1. **03:00** — cron pobiera nowe maile z nocy do Neon Postgres
2. **06:00** — klasyfikator (sklearn + Claude Haiku 4.5 dla niepewnych) oznacza każdy mail jako `spam` / `keep` / `uncertain`
3. Spam trafia do labela `_AI_TRASH` (archiwizowany, znika z INBOX, ale bezpieczny przez 7 dni)
4. Rano dostajesz WhatsApp "gotowe, X maili do przeglądu"
5. Wchodzisz na `https://spamgmail.vercel.app`, jeden klik = posprzątane lub cofnięte
6. Każda korekta = training set, model się uczy

## Stack

- **Hosting:** Vercel (Fluid Compute, Python 3.13 + Next.js)
- **DB:** Neon Postgres (free tier)
- **AI:** Vercel AI Gateway → Claude Haiku 4.5 (prompt caching) + scikit-learn
- **Cron:** Vercel Cron (`0 6 * * *` Europe/Warsaw)
- **Monorepo:** Turborepo

## Struktura

```
apps/web/        — Next.js — poranny przegląd
apps/api/        — Python Vercel Functions (cron, review)
packages/        — classifier, gmail, shared
scripts/         — bootstrap historii, retrening
docs/            — PRD, HLD, backlog, ADR, threat model
```

## Dokumentacja

- [PRD](docs/PRD.md) — Product Requirements
- [HLD](docs/HLD.md) — High-Level Design
- [Backlog](docs/backlog.md)

## Setup

```bash
npm install
vercel link
vercel env pull
npm run dev
```

## Status

🚧 **Sesja 1** — foundation, scaffold repo, lekka dokumentacja
