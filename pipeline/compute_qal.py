"""Compose served QaL records: works + cohort_percentiles + calibration_models -> qal_records.

For each work: look up observed percentile (universal layer, always present). If its
community is calibrated, attach the Layer-B posterior (point/interval/bucket probs) for
its (community, age, observed-pct bin); else mark calibration-pending.
"""
import os, json

def main():
    db = os.environ.get("DATABASE_URL")
    if not db:
        print("No DATABASE_URL; this job expects the datastore. See README."); return
    print("TODO: implement the join described in the docstring and upsert qal_records.")
    # left as the final POC step; see BUILD_BACKLOG.md milestone P5.

if __name__ == "__main__":
    main()
