# academic Ledger — QaL

Quality as a Ledger (**QaL**, said "qual"): a calibrated, continuously updated estimate of a paper's eventual standing in its field, built on the open scholarly record. Production site: **academic-ledger.org**.

Separates the two jobs academic publishing conflates: distribution (solved) and certification (rebuilt here as a measurement). See `docs/QaL_spec.md` for the full specification and `CLAUDE.md` for the build manual.

## Architecture
- **GitHub** — code + Actions (the batch pipeline runs here, monthly cron).
- **Vercel** — the Next.js web app + light read API (reads precomputed tables; never runs heavy compute). Custom domain academic-ledger.org.
- **Neon** — managed Postgres data layer.

```
docs/      QaL_spec.md (PRD), data_sourcing.md, mocks/ (the UI contract)
web/       Next.js app + read API (API_CONTRACT.md)
pipeline/  Python batch jobs (pull -> percentiles -> calibrate -> compute)
db/        schema.sql
.github/   workflows/refresh.yml (monthly batch)
```

## One-time setup (account actions are yours to do)
1. **GitHub**: repo lives at [ktulrich/AcademicLedger](https://github.com/ktulrich/AcademicLedger). Note: it is **public** (we changed it from the originally-planned private).
2. **Neon**: create a Postgres project; copy the pooled connection string; run `db/schema.sql`.
3. **Vercel**: create the project, connect it to the GitHub repo, add the custom domain `academic-ledger.org` (set the DNS records Vercel shows at your registrar).
4. **Secrets**: set `DATABASE_URL` and `OPENALEX_MAILTO` in (a) Vercel project env and (b) GitHub Actions secrets. Never commit them. Copy `.env.example` to `.env` for local dev.
5. **Claude Code**: open this repo; it will read `CLAUDE.md`.

OpenAlex needs no account — just the polite-pool email in `OPENALEX_MAILTO`.

## Develop
```bash
# pipeline
pip install -r pipeline/requirements.txt
python pipeline/pull_cohort.py --config pipeline/cohorts.yml   # writes Postgres, or JSONL if no DATABASE_URL
python pipeline/build_percentiles.py
python pipeline/calibrate.py
python pipeline/compute_qal.py

# web (after scaffolding Next.js in web/)
cd web && npm install && npm run dev
```

Status: research preview. All QaL values are illustrative pending calibration.
