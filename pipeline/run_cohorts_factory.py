"""Launch the COHORTS histogram factory (Exhibit E input) on a throwaway in-region EC2 box.

Same pattern as run_coverage_factory.py, but embeds factory_cohorts.py and reassembles the
gzip+base64 histogram blob that job streams over the serial console (FACTORY-COH DATA <idx> <b64>
chunks) back into a local JSON file. Self-terminating box; no Neon write.

Usage:
  python pipeline/run_cohorts_factory.py --file-limit 2                         # cheap plumbing smoke
  python pipeline/run_cohorts_factory.py --file-limit 0 --per 12000 --out PATH  # full run (~1h)
Needs AWS creds in ~/.aws/credentials (ClaudeCode).
"""
import os, sys, time, re, gzip, json, base64, argparse, boto3
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _env; _env.load_env()
REGION = "us-east-1"
DEFAULT_OUT = os.path.join(HERE, "..", "analysis", "gaming_robustness", "cohorts_hist.json")


def infra(ec2):
    vpc = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])["Vpcs"][0]["VpcId"]
    subnet = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc]}])["Subnets"][0]["SubnetId"]
    sg = ec2.describe_security_groups(Filters=[{"Name": "vpc-id", "Values": [vpc]},
                                               {"Name": "group-name", "Values": ["default"]}])["SecurityGroups"][0]["GroupId"]
    imgs = ec2.describe_images(Owners=["amazon"], Filters=[
        {"Name": "name", "Values": ["al2023-ami-2023.*-x86_64"]},
        {"Name": "state", "Values": ["available"]}])["Images"]
    ami = sorted(imgs, key=lambda i: i["CreationDate"])[-1]["ImageId"]
    return subnet, sg, ami


def user_data(file_limit, per):
    import gzip as _gz
    gz = lambda p: base64.b64encode(_gz.compress(open(os.path.join(HERE, p)).read().encode())).decode()
    b64_job = gz("factory_cohorts.py")
    return "\n".join([
        "#!/bin/bash",
        "echo '===FACTORY-BOOT==='",
        "dnf install -y python3-pip >/dev/null 2>&1",
        "pip3 install duckdb numpy 2>&1 | tail -1 | sed 's/^/FACTORY-PIP /'",
        f"echo {b64_job} | base64 -d | gunzip > /tmp/factory_cohorts.py",
        "echo FACTORY-STEP wrote job=$(wc -c < /tmp/factory_cohorts.py)",
        f"export FACTORY_FILE_LIMIT={file_limit}",
        f"export COH_PER={per}",
        "export DUCKDB_HOME=/tmp HOME=/tmp",
        "stdbuf -oL -eL python3 /tmp/factory_cohorts.py 2>&1 | sed 's/^/FACTORY-PY /'",
        # re-emit the chunk file repeatedly so the laggy, periodically-snapshotted console API captures a
        # COMPLETE set across polls (a one-shot burst before shutdown gets truncated/missed).
        "for i in $(seq 1 15); do echo FACTORY-COH REEMIT $i; cat /tmp/cohorts_out.txt; sleep 40; done",
        "echo '===FACTORY-EXIT==='",
        "shutdown -h +2",
    ])


DATA_RE = re.compile(r"FACTORY-COH DATA (\d+) (\d+) ([A-Za-z0-9+/=]+)")


def capture_chunks(console, chunks):
    """Strict parse of `FACTORY-COH DATA <idx> <len> <b64>` over the whole console buffer; only accept a
    chunk whose payload length matches the declared length (rejects console-garbled/truncated captures)."""
    for m in DATA_RE.finditer(console):
        idx, ln, payload = int(m.group(1)), int(m.group(2)), m.group(3)
        if len(payload) == ln:
            chunks[idx] = payload


def reassemble(chunks, out_path, expect_bytes=None, expect_chunks=None):
    # always persist raw chunks first, so a decode hiccup never forces a re-run
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    side = out_path + ".chunks.json"
    json.dump({str(k): v for k, v in chunks.items()}, open(side, "w"))
    if expect_chunks is not None and len(chunks) != expect_chunks:
        print(f"WARNING: have {len(chunks)}/{expect_chunks} chunks — raw saved to {side}; cannot decode.")
        return None
    blob = "".join(chunks[i] for i in sorted(chunks))
    if expect_bytes is not None and len(blob) != expect_bytes:
        print(f"WARNING: reassembled {len(blob)} b64 chars but job reported {expect_bytes}; "
              f"raw saved to {side}.")
        return None
    data = json.loads(gzip.decompress(base64.b64decode(blob)))
    json.dump(data, open(out_path, "w"))
    tot = sum(sum(v.values()) for v in data.values())
    print(f"wrote {out_path}: {len(data)} cohorts, {tot:,} papers")
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file-limit", type=int, default=2)
    ap.add_argument("--per", type=int, default=12000)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--instance-type", default="c6i.4xlarge")
    ap.add_argument("--max-minutes", type=int, default=150)
    a = ap.parse_args()

    ec2 = boto3.client("ec2", region_name=REGION)
    subnet, sg, ami = infra(ec2)
    print(f"infra: subnet={subnet} sg={sg} ami={ami}")
    r = ec2.run_instances(ImageId=ami, InstanceType=a.instance_type, MinCount=1, MaxCount=1,
        SecurityGroupIds=[sg], SubnetId=subnet, InstanceInitiatedShutdownBehavior="terminate",
        BlockDeviceMappings=[{"DeviceName": "/dev/xvda", "Ebs": {"VolumeSize": 30, "VolumeType": "gp3"}}],
        UserData=user_data(a.file_limit, a.per),
        TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "cohorts-factory"}]}])
    iid = r["Instances"][0]["InstanceId"]
    print(f"launched {iid} ({a.instance_type}, file-limit={a.file_limit}); watching console...")

    seen = set(); chunks = {}; expect = None; nchunks = None; deadline = time.time() + a.max_minutes * 60
    try:
        while time.time() < deadline:
            time.sleep(30)
            out = ec2.get_console_output(InstanceId=iid, Latest=True).get("Output", "")
            if "===FACTORY" not in out:
                try: out = base64.b64decode(out).decode("utf-8", "replace")
                except Exception: pass
            capture_chunks(out, chunks)   # accumulate across polls (buffer scrolls; re-emitted repeatedly)
            for ln in out.splitlines():
                if "FACTORY" not in ln or ln in seen or "FACTORY-COH DATA " in ln:
                    continue
                seen.add(ln)
                clean = ln.split("cloud-init")[-1].lstrip("]: ").strip()
                if "FACTORY-COH BYTES " in clean:
                    m = re.search(r"BYTES (\d+) chunks (\d+)", clean)
                    if m: expect, nchunks = int(m.group(1)), int(m.group(2))
                if "REEMIT" not in clean:
                    print("  " + clean)
            if nchunks:
                print(f"  ... captured {len(chunks)}/{nchunks} chunks")
            if nchunks and len(chunks) >= nchunks:
                print(f"all {nchunks} chunks captured — stopping early."); break
            if "===FACTORY-EXIT===" in out:
                print(f"cohorts factory finished; {len(chunks)}/{nchunks} data chunks captured."); break
        else:
            print(f"watch timed out after {a.max_minutes} min (instance self-terminates).")
    finally:
        ec2.terminate_instances(InstanceIds=[iid]); print(f"terminated {iid}")

    if chunks:
        reassemble(chunks, a.out, expect, nchunks)
    else:
        print("no data chunks captured — nothing written.")


if __name__ == "__main__":
    main()
