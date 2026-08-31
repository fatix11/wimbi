# Wimbi

Farmer 360 for OAF — a role-based web app giving staff a unified view of a
farmer's history across programs (credit, trees, sales, buyback).

Read `_docs/business_requirements.md`, `_docs/features_and_user_stories.md`,
and `_docs/delivery_strategy.md` first — they're the maintained source of
truth for what this is and how it's meant to be built. `_docs/to_do.md`
tracks live progress.

## Current state

This is the first vertical slice toward the October internal MVP: farmer
search + Farmer Journey Timeline, RBAC-scoped by country, running against
mock fixture data (no live Snowflake/Keycloak yet — see below).

## Getting started

```bash
npm install
cp .env.local.example .env.local   # then fill in AUTH_SECRET (npx auth secret)
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) — you'll land on a dev
login page (stand-in for Keycloak SSO) listing a few fake personas to sign in
as. Pick one, search a fixture farmer (try "Grace", or `GL-MW-00001`), and
open their profile to see the Journey Timeline.

## Swapping in real backends

- **Data**: set `WIMBI_DATA_SOURCE=snowflake` and fill in the `SNOWFLAKE_*`
  vars in `.env.local` once ANALYTICS.REPORTING credentials exist. The app
  code doesn't change — `src/data/source.ts` picks the implementation.
- **Auth**: once an OAF Keycloak realm/client exists, add next-auth's OIDC
  provider in `src/auth/config.ts` alongside (or instead of) the dev
  Credentials provider — the session shape (`country`/`department`/`role`)
  and every RBAC check downstream are already built against that contract.

## Testing

```bash
npm run test       # unit tests (Vitest) — includes RBAC negative tests
npm run test:e2e   # end-to-end (Playwright) — login -> search -> timeline
npm run lint
npm run build
```
