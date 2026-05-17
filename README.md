# Hockey Calgary Analytics

Community-level analytics for Calgary minor hockey, 2020–present. Scrapes
standings from Hockey Calgary, Alberta One (RAMP), and TeamLinkt; stores them
in Postgres; surfaces them in a Next.js dashboard with two main views — a
filterable analytics page and a tier-1 dilution analysis.

Live at https://hockey-calgary-scraper.onrender.com.

> Personal-interest project. Not an authoritative source — the underlying
> data's accuracy depends on what the upstream sites publish.

## Architecture

```
┌─────────────────────────┐         ┌─────────────────────────┐
│   web/  (Next.js 16)    │   SQL   │  Postgres (Neon in      │
│   Fluent UI v9          │ ──────► │  prod, Docker locally)  │
│   Drizzle ORM           │         └─────────────────────────┘
└──────────┬──────────────┘                      ▲
           │ POST /api/scraper/run               │
           │ (admin-gated; spawns python3        │
           │  detached)                          │
           ▼                                     │
┌─────────────────────────┐                      │
│   scraper.py  (Python)  │ ─── SQLAlchemy ──────┘
│   requests + bs4 +      │
│   pdfplumber            │
└─────────────────────────┘
```

- **Web app (`web/`)** — Next.js 16 App Router + Fluent UI v9 + Drizzle.
  Server components read Postgres directly; client components handle filter
  state and charts (Recharts). Deployed as a Docker image to Render.
- **Scraper (`scraper.py`)** — Python script invoked manually via the web
  app's admin gate. Writes rows to `standings` + `scrape_runs`. Same Postgres
  as the web app, so changes are visible on next page load.
- **Schema (`models.py`, `alembic/`)** — SQLAlchemy models, Alembic
  migrations. The Drizzle schema in `web/src/lib/db/schema.ts` mirrors the
  Python models; Alembic owns DDL.

## Local development

### Prereqs

- Node 20+ (we test on 22)
- Python 3.11+
- Docker (for local Postgres) — or any Postgres you prefer

### Setup

1. **Postgres** — start the bundled docker compose stack:

   ```sh
   docker compose up -d
   ```

   Brings up Postgres 16 at `localhost:5432`, user `hockey`, DB
   `hockey_calgary`. Tear down with `docker compose down`.

2. **Env vars** — create a `.env` in the repo root (`.gitignore` excludes
   it):

   ```
   DATABASE_URL=postgresql+psycopg://hockey:hockey@localhost:5432/hockey_calgary
   ADMIN_PASSWORD=<pick something>
   ```

3. **Python deps + initial scrape** — to populate the DB:

   ```sh
   pip install -r requirements.txt
   python scraper.py            # incremental
   # or: python scraper.py --reset    (full rebuild, drops first)
   ```

   Takes ~15 minutes for a full scrape. The web app reads the same DB, so
   you can also trigger scrapes from its admin UI (step 4).

4. **Web app** — runs on http://localhost:3000:

   ```sh
   cd web
   npm install
   npm run dev
   ```

   The web app picks up `DATABASE_URL` and `ADMIN_PASSWORD` from the parent
   `../.env`.

### Database migrations

Alembic owns the schema. New migrations:

```sh
alembic revision --autogenerate -m "<message>"
alembic upgrade head
```

The scraper's `init_db()` applies pending migrations on first run. For pure
web-app dev (no scraper invocation), run `alembic upgrade head` manually
before `npm run dev`.

## Deployment

The app deploys as a single Docker image to Render. The image bundles both
Node (for the Next.js server) and Python (for the scraper subprocess) so the
admin "Run Scraper" button can spawn the scraper inside the same container.

### Render setup

1. New → **Web Service** → connect this repo.
2. **Runtime**: Docker. Dockerfile path: `./Dockerfile`.
3. Environment variables:

   | Key              | Value                                  |
   | ---------------- | -------------------------------------- |
   | `DATABASE_URL`   | Neon connection string                 |
   | `ADMIN_PASSWORD` | secret of your choosing                |
   | `PYTHON_BIN`     | `python3`                              |

4. Health check path: `/`.

Pushes to `main` auto-deploy.

### Running a scrape in production

1. Open the deployed app.
2. Click the lock icon in the top bar → enter `ADMIN_PASSWORD` → Unlock.
3. Click **Run scraper**. Choose *Update* (additive) or *Full reset*.
4. The page shows a live progress banner with elapsed time + the latest log
   line, and auto-refreshes when the run finishes.

> ⚠️ The scraper subprocess runs inside the web container. A Render restart
> or redeploy mid-scrape will kill it. Fine for manual single-user use;
> fragile for unattended cron. Moving the scraper to a separate Render
> service is on the roadmap.

## Project layout

```
.
├── scraper.py              # Python scraper (~1300 lines)
├── models.py               # SQLAlchemy schema
├── database.py             # SQLAlchemy engine + init_db()
├── alembic/                # DB migrations
├── utilities/              # Shared Python helpers (tiering, team labels)
├── data/reference/         # Static reference data (community → neighborhood etc.)
├── scripts/                # One-off maintenance / inspection scripts
├── docker-compose.yml      # Local Postgres
├── Dockerfile              # Production image (Node + Python)
└── web/                    # Next.js app
    └── src/
        ├── app/
        │   ├── page.tsx               # / — Analytics page
        │   ├── analytics/             # Analytics page components
        │   ├── dilution/              # /dilution — Tier 1 Dilution
        │   └── api/
        │       ├── admin/             # unlock / lock
        │       └── scraper/           # run / status / log
        ├── components/                # Shared client components
        └── lib/
            ├── db/                    # Drizzle + pg pool
            └── analytics/             # Filter + computation logic
```

## License

MIT.
