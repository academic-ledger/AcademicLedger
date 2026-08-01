"""Launch the cross-field COVERAGE factory (Exhibit C) on a throwaway in-region EC2 box.

Same pattern as factory_launch.py: self-runs from user-data, reports via serial console, self-
terminates. Embeds calib_lib.py + factory_coverage.py; no Neon write (prints coverage to console).

Usage:
  python pipeline/run_coverage_factory.py --file-limit 2                 # cheap plumbing smoke
  python pipeline/run_coverage_factory.py --file-limit 0 --per 10000     # full run (~1h)
Needs AWS creds in ~/.aws/credentials (ClaudeCode).
"""
import os, sys, time, base64, argparse, boto3
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _env; _env.load_env()   # AWS creds + DATABASE_URL from repo .env (no secret printed)
REGION = "us-east-1"


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
    import gzip
    gz = lambda p: base64.b64encode(gzip.compress(open(os.path.join(HERE, p)).read().encode())).decode()
    b64_calib = gz("calib_lib.py")   # gzip: EC2 user-data is capped at 16 KB
    b64_job = gz("factory_coverage.py")
    return "\n".join([
        "#!/bin/bash",
        "echo '===FACTORY-BOOT==='",
        "dnf install -y python3-pip >/dev/null 2>&1",
        "pip3 install duckdb numpy 2>&1 | tail -2 | sed 's/^/FACTORY-PIP /'",
        f"echo {b64_calib} | base64 -d | gunzip > /tmp/calib_lib.py",
        f"echo {b64_job} | base64 -d | gunzip > /tmp/factory_coverage.py",
        "echo FACTORY-STEP wrote calib=$(wc -c < /tmp/calib_lib.py) job=$(wc -c < /tmp/factory_coverage.py)",
        f"export FACTORY_FILE_LIMIT={file_limit}",
        f"export COV_PER={per}",
        "export DUCKDB_HOME=/tmp HOME=/tmp",
        "stdbuf -oL -eL python3 /tmp/factory_coverage.py 2>&1 | sed 's/^/FACTORY-PY /'",
        "echo '===FACTORY-EXIT==='",
        "shutdown -h +5",
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file-limit", type=int, default=2)
    ap.add_argument("--per", type=int, default=8000)
    ap.add_argument("--instance-type", default="c6i.4xlarge")
    ap.add_argument("--max-minutes", type=int, default=100)
    a = ap.parse_args()

    ec2 = boto3.client("ec2", region_name=REGION)
    subnet, sg, ami = infra(ec2)
    print(f"infra: subnet={subnet} sg={sg} ami={ami}")
    r = ec2.run_instances(ImageId=ami, InstanceType=a.instance_type, MinCount=1, MaxCount=1,
        SecurityGroupIds=[sg], SubnetId=subnet, InstanceInitiatedShutdownBehavior="terminate",
        BlockDeviceMappings=[{"DeviceName": "/dev/xvda", "Ebs": {"VolumeSize": 30, "VolumeType": "gp3"}}],
        UserData=user_data(a.file_limit, a.per),
        TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "coverage-factory"}]}])
    iid = r["Instances"][0]["InstanceId"]
    print(f"launched {iid} ({a.instance_type}, file-limit={a.file_limit}); watching console...")

    seen = set(); deadline = time.time() + a.max_minutes * 60
    try:
        while time.time() < deadline:
            time.sleep(30)
            out = ec2.get_console_output(InstanceId=iid, Latest=True).get("Output", "")
            if "===FACTORY" not in out:
                try: out = base64.b64decode(out).decode("utf-8", "replace")
                except Exception: pass
            for ln in out.splitlines():
                if "FACTORY" in ln and ln not in seen:
                    seen.add(ln); print("  " + ln.split("cloud-init")[-1].lstrip("]: ").strip())
            if "===FACTORY-EXIT===" in out:
                print("coverage factory finished."); break
        else:
            print(f"watch timed out after {a.max_minutes} min (instance self-terminates).")
    finally:
        ec2.terminate_instances(InstanceIds=[iid]); print(f"terminated {iid}")


if __name__ == "__main__":
    main()
