"""Launch the in-region OpenAlex factory on a throwaway EC2 box, watch it, tear it down.

Why EC2: this network blocks outbound 22 AND 5432, so we can neither SSH nor write Neon from
here. An EC2 box in us-east-1 sits next to both the OpenAlex snapshot (S3) and Neon, reads fast,
and writes Neon with no firewall. No inbound is opened; the box self-runs `factory.py` from
user-data and reports via the serial console (read over 443). See academic-ledger-aws-factory memory.

Usage:
  python pipeline/factory_launch.py --file-limit 200 --snapshot factory-slice-test    # slice
  python pipeline/factory_launch.py --snapshot openalex-2026-06                         # full corpus
Needs DATABASE_URL in .env and AWS creds in ~/.aws/credentials (ClaudeCode, EC2 scope).
"""
import os, sys, time, base64, argparse, boto3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _env; _env.load_env()

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


def user_data(file_limit, snapshot, min_n):
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "factory.py")).read()
    b64_src = base64.b64encode(src.encode()).decode()
    b64_db = base64.b64encode(os.environ["DATABASE_URL"].encode()).decode()  # never printed
    return "\n".join([
        "#!/bin/bash",
        "echo '===FACTORY-BOOT==='",
        "dnf install -y python3-pip >/dev/null 2>&1",
        "pip3 install duckdb 'psycopg[binary]' >/dev/null 2>&1",
        f"echo {b64_src} | base64 -d > /tmp/factory.py",
        f"export DATABASE_URL=$(echo {b64_db} | base64 -d)",
        f"export FACTORY_FILE_LIMIT={file_limit}",
        f"export OPENALEX_SNAPSHOT='{snapshot}'",
        f"export MIN_COHORT_N={min_n}",
        "export DUCKDB_HOME=/tmp HOME=/tmp",
        "HOME=/tmp python3 /tmp/factory.py 2>&1",
        "echo '===FACTORY-EXIT==='",
        "shutdown -h +5",            # backstop: self-terminate even if we lose the watcher
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file-limit", type=int, default=0, help="0 = full corpus")
    ap.add_argument("--snapshot", default="openalex-dev")
    ap.add_argument("--min-n", type=int, default=50)
    ap.add_argument("--instance-type", default="c6i.4xlarge")
    ap.add_argument("--max-minutes", type=int, default=120)
    a = ap.parse_args()

    ec2 = boto3.client("ec2", region_name=REGION)
    subnet, sg, ami = infra(ec2)
    print(f"infra: subnet={subnet} sg={sg} ami={ami}")

    r = ec2.run_instances(ImageId=ami, InstanceType=a.instance_type, MinCount=1, MaxCount=1,
        SecurityGroupIds=[sg], SubnetId=subnet, InstanceInitiatedShutdownBehavior="terminate",
        BlockDeviceMappings=[{"DeviceName": "/dev/xvda", "Ebs": {"VolumeSize": 30, "VolumeType": "gp3"}}],
        UserData=user_data(a.file_limit, a.snapshot, a.min_n),
        TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "factory"}]}])
    iid = r["Instances"][0]["InstanceId"]
    print(f"launched {iid} ({a.instance_type}); watching console...")

    seen = set()
    deadline = time.time() + a.max_minutes * 60
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
                print("factory finished."); break
        else:
            print(f"watch timed out after {a.max_minutes} min (instance will self-terminate).")
    finally:
        ec2.terminate_instances(InstanceIds=[iid])
        print(f"terminated {iid}")


if __name__ == "__main__":
    main()
