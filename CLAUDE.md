# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Automatic-Reporting is SUDENE's municipal report generator: a FastAPI service that
builds per-city, per-macrotheme reports as HTML and PDF. Each report combines three
sources — tabular data (PostgreSQL views/tables, with Google Sheets CSV as fallback),
editorial prose (one Google Doc per macrotheme), and charts (matplotlib) — renders
them through a React SSR layer, and converts the result to PDF with WeasyPrint. It is
the backend behind the sibling `data-nordeste-frontend` portal.

There are eight macrotemas (demografia, educação, saúde, economia-renda, hidráulica,
desenvolvimento-social, meio-ambiente, saneamento). The data is real and lives in the
Data Nordeste PostgreSQL instance — this repo ships no dump or migrations, so the full
pipeline only runs against that database (see README for credentials).

Companion docs, read them instead of re-deriving their content:

- `docs/ARCHITECTURE.md` — the pipeline end to end: data → docs → placeholders →
  React SSR → PDF, the directory map, the SSR props dictionary, and the build steps
  (pt-BR). The authoritative architecture reference.
- `README.md` — local setup, env, and Docker flow (pt-BR).
- `.env.example` — the authoritative list of environment variable names (CSV URLs,
  Doc URLs, DB connection). Never commit a real `.env`.
- `docs/editorial/` — the rules editors follow when writing a macrotheme's Google Doc
  (block markers, `$placeholders`, editorial conditionals).

## Learning is part of the work

This team builds software and teaches people to build it at the same time. Both count.
A session succeeds when it produces a correct change _and_ a developer who can explain
and defend it in review. Everyone is new to some subsystem here — the data layer, the
Docs template language, the SSR/PDF pipeline.

**Confirm the diagnosis before applying a fix.** Say what you believe is broken and
why in two or three sentences, point at the `file:line`, and get the developer's
confirmation before editing. A fix they cannot explain is a fix they cannot review.

Other moments worth one focused question:

- **Ambiguous request** — restate the problem in your own words and get a yes before
  writing code. Cheaper than a wrong implementation.
- **Failing test or crash** — show the real output and ask what they think caused it
  before diagnosing. Hypothesis first; patching until green is not the skill.
- **Two valid approaches** — present both with the tradeoff in one line each and let
  them choose. Don't silently pick.
- **Touching a guard** — the DB `statement_timeout`, the view/CSV fallback, the
  `nm_mun` canonicalization, the placeholder tolerance (see _Guards_ below). Explain
  what breaks if it goes, then get an explicit yes.
- **Root cause is outside this repo** — the data lives in Data Nordeste's PostgreSQL,
  the prose in Google Docs editable by non-devs. If the number is wrong in the view or
  the sentence is wrong in the Doc, no Python edit fixes it. Say so plainly.
- **Change is done** — summarize what changed and why, in the shape of a commit message
  they can reuse, and check it matches their understanding.

Limits, so this stays help and not friction: one focused question, never a quiz; never
withhold an answer to teach — explain, then confirm; if they say just do it, or
production is broken, fix first and teach after. Mechanical work — typos, formatting,
renames — needs no checkpoint.

## Commands

```bash
cp .env.example .env         # fill in CSV/Doc URLs and DB connection; never commit it
pip install -r requirements.txt
npm install                  # root workspaces: frontend + report
npm run build -w report      # SSR bundle (report/ssr-dist) — required before the API renders
npm run build -w frontend    # browser SPA

uvicorn main:app --reload    # http://localhost:8000 ; spawns the node SSR server on startup
python -m pytest             # test suite
python -m pytest tests/test_saneamento_chart.py -q   # single file
ruff check .                 # lint (the CI gate)
ruff check plotting/saneamento.py                    # single file
```

To generate a report by hand: `GET /relatorio/{cidade}?macrotema=saneamento` (e.g.
`Campina Grande (PB)`). It writes `output/relatorio_<slug>.{html,pdf}` and returns the
HTML. `GET /cities` and `GET /macrotemas` are cheap health/list endpoints.

**Real data needs the DB tunnel first** (see _Guards_). Without it every `buscar_*`
returns `None` and the report falls back to CSV or leaves placeholders empty.

Validation before finishing a change:

- `ruff check .` — always.
- `python -m pytest` — when touching data, rendering, or plotting logic, and for every
  bug fix.
- `npm run build -w report` — after editing anything under `report/src` (the SSR
  React components); the running API uses the built bundle, not the source.

CI (`.github/workflows/ci.yaml`) only runs `ruff check .`, builds the bundles, and
health-checks the API — **it does not run pytest**. The test suite is a local gate; run
it yourself.

## Architecture

Read `docs/ARCHITECTURE.md` for the full flow. The short version — a report is one pass
through these layers, orchestrated by `services/generation.py:gerar_relatorio_handler`:

- **Data** — `utils/queries/<tema>.py` holds `buscar_*` functions (pure: take
  `nome_municipio, sigla_uf`, return a flat `{placeholder: valor}` dict, or `None`).
  `utils/queries/perfil_municipal.py` reads the primary source — the
  `relatorios_auto.vw_perfil_*` view per macrotheme; CSV (Google Sheets) is the
  fallback. `utils/queries/base.py` runs the SQL; `utils/database.py` connects from
  `.env`. The merged row is the report's `contexto`.
- **Prose** — `utils/external/docs.py` fetches and caches the macrotheme's Google Doc
  (export as txt, ETag cache in `output/docs_cache/`) and slices it by block marker.
- **Render** — `utils/render/placeholders.py` resolves `$campo` (and `namespace.$campo`)
  against the `contexto`, plus editorial conditionals and aliases;
  `utils/render/renderer.py` turns the template text into HTML (headings, lists,
  charts, the region map).
- **Charts** — `plotting/<tema>.py`, matplotlib, one function per chart, reading either
  a flat row from `contexto` or a `*_serie` list. Wired into `graficos_por_placeholder`
  in `services/generation.py`.
- **SSR + PDF** — `utils/ssr.py` renders the React report (`report/`) via a persistent
  node server started at FastAPI startup; `services/pdf.py` converts the HTML to PDF
  with WeasyPrint.
- **Metadata** — `utils/data/macrotemas.py` describes the eight macrotemas (name,
  color, Doc/CSV env keys, section number).

## Guards you must not soften

- **The DB is reached through an SSH tunnel.** `.env` points `DB_HOST/DB_PORT` at a
  local forwarded port, not the database directly; bring the tunnel up before anything
  that touches the DB or `psycopg2` times out. Ask the team for the host and tunnel
  command — they are not in this repo.
- **`executar_query` swallows errors and returns `None`** by design — a failing query
  becomes "no data", not an exception. Don't turn that into a raise; the report is
  meant to degrade (CSV fallback / empty placeholder), not 500.
- **Never `SELECT *` a `vw_perfil_*` view without a `statement_timeout` and a specific
  city in `WHERE`.** These are heavy aggregations; running several unbounded ones at
  once can exhaust the database host's memory.
- **The view is primary, CSV is the fallback** (PR #91). Keep both paths working; a
  view that lacks a city must fall through to CSV, not error.
- **A null variable hides the block that depends on it.** Prose coming from the panel's
  contract (`utils/editorial/render.py`) drops any paragraph, caption or list item whose
  `$campo` doesn't resolve for that city, and a section left with no children drops its
  heading too — a `$sol_predom` printed raw in a mayor's report is worse than the
  sentence not being there. Write the "no data" wording as another block guarded by a
  rule when the trecho should survive. Prose still coming from a Google Doc keeps the old
  behaviour (the placeholder prints literally), which is one more reason to migrate a
  macrotheme to the panel. A `namespace.$campo` whose namespace is another view (e.g.
  `demografia.$nm_mun` in a saneamento report) resolves against the merged `contexto`.
- **`nm_mun` is canonicalized to `"Cidade (UF)"`** in `generation.py` before the
  downstream `buscar_*` run, because their joins match `nm_mun` case-sensitively. Don't
  pass the user's raw typed name through.
- **Charts insert into the Doc by caption regex** (`GRAFICOS_AUTO_MARCADOR` in
  `services/generation.py`): the marker is injected above a `Figura N – <legenda>` line
  that the regex matches. No caption in the Doc → no chart. The Doc is edited by
  non-devs; coordinate the caption text with them.
- **The map needs shapefiles that aren't in the repo** (`scripts/download_map_shapes.py`,
  `MAP_SHAPE_ZIP_URL`), and the **VM runs in UTC** (log timestamps are UTC; BRT = −3h).

## Adding or changing a macrotheme chart

The recurring task. Mirror an existing theme (`plotting/saude.py` and the `saude` block
in `generation.py` are the fullest example):

1. **Data** — if the chart's numbers are already columns on the perfil view, read them
   straight from `contexto`; otherwise add a `buscar_*` in `utils/queries/<tema>.py`
   against the raw schema and merge it into `contexto` in `generation.py`.
2. **Plot** — add `gerar_grafico_<nome>(cidade, OUTPUT_DIR, safe_city) -> str` in
   `plotting/<tema>.py`. Reuse the formatting helpers; raise `ValueError` when data is
   missing so `generation.py` can skip the chart with a warning.
3. **Wire** — call it under `if macrotema_slug == "<tema>":` and store the filename in
   `graficos_por_placeholder["grafico_<nome>"]`.
4. **Insert** — add a `(nome_grafico, legenda_regex)` entry to
   `GRAFICOS_AUTO_MARCADOR["<tema>"]` matching the Doc's `Figura N – <legenda>`, **and**
   make sure that caption exists in the Google Doc.
5. **Test** — a `tests/test_<tema>_chart.py` that feeds a synthetic `contexto` and
   asserts the PNG is written (no DB).

## Code style

- Match the surrounding code — this is a Python codebase with **pt-BR names and
  comments**; keep that language in new code near existing pt-BR code.
- `buscar_*` functions are pure and flat: input `(nome, uf)`, output a `{placeholder:
  valor}` dict or `None`. No side effects, no rendering.
- Small, single-responsibility functions; type hints on signatures.
- Prefer reading from the merged `contexto` over adding a new query when the value is
  already there.
- `ruff` is the lint authority (`ruff check .`). Don't argue style beyond it.

## Comments

- Keep existing comments; they carry intent and provenance. Don't strip them on refactor.
- Write WHY, not WHAT. Put the comment next to the guard, query, or compatibility branch
  it explains — several load-bearing comments already sit next to the DB timeout, the
  `nm_mun` canonicalization, and the placeholder fallbacks.
- Reference PR/issue numbers when a line exists because of a specific fix (e.g. the
  primary-view migration is PR #91).

## Tests

- `pytest`, co-located under `tests/`. Per-theme charts and queries have their own files
  (`tests/test_<tema>_chart.py`, `tests/test_<tema>_query.py`); the placeholder resolver
  and Doc extractors have `tests/test_docs_renderer.py` / `test_docs_extractors.py`.
- Chart tests feed a synthetic `contexto` and assert the PNG is written — they must not
  touch the database. Query tests that need the DB are the exception, not the rule.
- Every new chart or query gets a test; every bug fix gets a regression test.
- CI does not run them — running `python -m pytest` before you finish is the only gate.

## Git conventions

- **Conventional-commit-style subjects** (`feat:`, `fix:`, `chore:`, `docs:`, with a
  scope like `feat(saneamento):`). The `git log` history predates this and contains
  invalid types (`add: ...`) — do not infer the style from it.
- **Commit only when asked**, one concern per branch. This session's work is a good
  shape: the saneamento chart, the score removal, and this doc are three separate
  branches off `main`.
- **No `Co-Authored-By` trailer** — matching the team's convention in
  `data-nordeste-frontend`: agent-assisted commits are not marked; the developer in
  `git config user.name` is the author and answers for the change.
