#!/usr/bin/env python3
"""Download translation files from ParaTranz.

Usage:
    PZ_TOKEN=xxx PZ_PROJECT_ID=12345 python3 scripts/fetch_pz.py [--out pz_export/] [--no-trigger]

Environment variables:
    PZ_TOKEN       - ParaTranz API token (required)
    PZ_PROJECT_ID  - ParaTranz project ID (required)
"""
import argparse
import json
import os
import shutil
import sys
import time
import zipfile
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE_URL = "https://paratranz.cn/api"


def api_request(path, token, method="GET", timeout=60):
    url = "{}{}".format(BASE_URL, path)
    req = Request(url, method=method)
    req.add_header("Authorization", token)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except HTTPError as e:
        print("HTTP {} for {}: {}".format(e.code, url, e.read().decode()[:200]),
              file=sys.stderr)
        raise


def trigger_export(project_id, token):
    """Trigger artifact build on PZ."""
    print("Triggering PZ artifact build...")
    api_request("/projects/{}/artifacts".format(project_id), token, method="POST")
    for i in range(30):
        time.sleep(5)
        print("  waiting... ({}s)".format((i + 1) * 5))
        try:
            data = api_request("/projects/{}/artifacts".format(project_id), token)
            if len(data) > 100:
                return data
        except HTTPError:
            continue
    raise RuntimeError("Artifact build timed out")


def download_artifact(project_id, token):
    """Download the latest artifact zip."""
    print("Downloading PZ artifact...")
    return api_request(
        "/projects/{}/artifacts/download".format(project_id), token, timeout=120)


def main():
    parser = argparse.ArgumentParser(description="Fetch translations from ParaTranz")
    parser.add_argument("--out", default="pz_export", help="Output directory")
    parser.add_argument("--no-trigger", action="store_true",
                        help="Skip triggering build, just download latest")
    args = parser.parse_args()

    token = os.environ.get("PZ_TOKEN")
    if not token:
        print("Error: PZ_TOKEN environment variable required", file=sys.stderr)
        sys.exit(1)

    project_id = os.environ.get("PZ_PROJECT_ID")
    if not project_id:
        print("Error: PZ_PROJECT_ID environment variable required", file=sys.stderr)
        sys.exit(1)

    if not args.no_trigger:
        trigger_export(project_id, token)

    data = download_artifact(project_id, token)
    print("  downloaded {} KB".format(len(data) // 1024))

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)

    with zipfile.ZipFile(BytesIO(data)) as zf:
        names = zf.namelist()
        prefix = ""
        if names and "/" in names[0]:
            prefix = names[0].split("/")[0] + "/"

        for name in names:
            if name.endswith("/"):
                continue
            rel = name[len(prefix):] if name.startswith(prefix) else name
            target = out / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "wb") as f:
                f.write(zf.read(name))

    file_count = sum(1 for _ in out.rglob("*.json"))
    print("  extracted {} JSON files to {}/".format(file_count, out))
    print("Done!")


if __name__ == "__main__":
    main()
