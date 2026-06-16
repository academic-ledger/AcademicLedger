"""Drain synth_view_queue: compute + persist the synthetic field for papers that were viewed
without a cached blend (enqueued by the web paper page, migration 005). Runs on the FREE polite
pool by default — heavy compute stays off the request path (Vercel does no heavy compute) and off
the metered OpenAlex budget. Resumable and idempotent: each blend is upserted into synthetic_field
and the oaid removed from the queue; repeated failures bump an attempt counter and are skipped past
a cap. The next paper view (read-through) and Explore then serve the cached blend.

Run:  python pipeline/synth_worker.py [--limit N] [--use-premium] [--max-attempts K]
Schedule alongside the other launchd jobs once it's proven.
"""
import os
import argparse

import _env
_env.load_env()

import synthetic_field as sf  # reuse the exact blend computation + upsert (defaults handled below)


def _dequeue(db, oaid):
    import psycopg
    with psycopg.connect(db) as c, c.cursor() as cur:
        cur.execute("DELETE FROM synth_view_queue WHERE oaid=%s", (oaid,))


def _bump(db, oaid, err):
    import psycopg
    with psycopg.connect(db) as c, c.cursor() as cur:
        cur.execute("UPDATE synth_view_queue SET attempts=attempts+1, last_error=%s WHERE oaid=%s",
                    (err, oaid))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--max-attempts", type=int, default=5)
    ap.add_argument("--use-premium", action="store_true",
                    help="use the metered premium key (default: free polite pool)")
    args = ap.parse_args()

    if not args.use_premium:
        sf.API_KEY = ""  # free polite pool by default — the worker must never silently bill

    db = os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL not set")

    import psycopg
    # claim a batch: queued, under the attempt cap, and not already computed (parts present)
    with psycopg.connect(db) as c, c.cursor() as cur:
        # Prioritize by citations: public crawlers enqueue the whole long tail, so compute the
        # papers people actually care about first (highest-cited), not merely first-crawled.
        cur.execute(
            """SELECT q.oaid FROM synth_view_queue q
                 LEFT JOIN qal_records r ON r.oaid = q.oaid
                WHERE q.attempts < %s
                  AND NOT EXISTS (SELECT 1 FROM synthetic_field s
                                   WHERE s.oaid=q.oaid AND s.parts IS NOT NULL)
                ORDER BY (r.display->>'cites')::int DESC NULLS LAST
                LIMIT %s""",
            (args.max_attempts, args.limit))
        oaids = [r[0] for r in cur.fetchall()]
        # drop any queued rows already satisfied (computed by the backfill/compute_qal meanwhile)
        cur.execute(
            """DELETE FROM synth_view_queue q
                WHERE EXISTS (SELECT 1 FROM synthetic_field s
                               WHERE s.oaid=q.oaid AND s.parts IS NOT NULL)""")
        c.commit()

    pool = "premium (metered)" if args.use_premium else "polite (free)"
    print(f"synth-view worker: pool={pool}; {len(oaids)} papers to compute", flush=True)
    done = 0
    for i, oaid in enumerate(oaids, 1):
        try:
            rec = sf.synthetic_field(oaid)
        except Exception as e:  # network/retries-exhausted/cap — record and move on
            _bump(db, oaid, str(e)[:200])
            print(f"  [{i}] {oaid}: error ({str(e)[:60]})", flush=True)
            continue
        if rec:
            sf._upsert(db, rec)
            _dequeue(db, oaid)
            done += 1
        else:
            _bump(db, oaid, "synthetic_field returned None (could not place)")
        if i % 25 == 0:
            print(f"  [{i}/{len(oaids)}] persisted={done}", flush=True)
    print(f"done: persisted {done} blends ({len(oaids) - done} unresolved this run)", flush=True)


if __name__ == "__main__":
    main()
