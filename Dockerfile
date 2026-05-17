# syntax=docker/dockerfile:1.7

# -----------------------------------------------------------------------------
# Single image that serves the Next.js web app *and* carries the Python scraper
# along with its dependencies. The web app's "Run Scraper" admin button spawns
# `python3 scraper.py` from a Node API route, so both runtimes need to live in
# the same container for that to work without IPC across services.
# -----------------------------------------------------------------------------

# ----- Stage 1: build the Next.js standalone bundle -------------------------
FROM node:20-bookworm-slim AS web-build
WORKDIR /app/web

# Copy manifests first to maximise layer caching.
COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build


# ----- Stage 2: runtime ------------------------------------------------------
FROM node:20-bookworm-slim AS runtime

# Python + system deps the scraper needs (pdfplumber → cairo/poppler? no, just
# stdlib via pypdfium2; psycopg → libpq).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        libpq5 \
        ca-certificates \
        tini \
    && rm -rf /var/lib/apt/lists/*

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PYTHON_BIN=python3 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Python deps (in a venv to avoid PEP 668 friction on Debian).
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Python scraper + the files it loads at runtime.
COPY scraper.py models.py database.py alembic.ini ./
COPY utilities/ ./utilities/
COPY alembic/ ./alembic/
COPY data/ ./data/
COPY community_map.json association_neighborhoods.json calgary_2021_census_incomes.json neighborhood_incomes.json ./

# Next.js standalone bundle. The build output puts `server.js` at the root of
# the standalone tree, plus a minimal `node_modules/`. Static assets and
# `public/` are not included in standalone and must be copied separately.
COPY --from=web-build /app/web/.next/standalone/ ./web/
COPY --from=web-build /app/web/.next/static ./web/.next/static
COPY --from=web-build /app/web/public ./web/public

# Render exposes whichever PORT it injects; default to 10000 locally.
ENV PORT=10000
EXPOSE 10000

# `tini` reaps zombie child processes — important because the API route spawns
# `python3 scraper.py` detached and we don't want orphans accumulating.
ENTRYPOINT ["/usr/bin/tini", "--"]
WORKDIR /app/web
CMD ["node", "server.js"]
