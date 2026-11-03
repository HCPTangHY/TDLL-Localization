#!/usr/bin/env python3
"""Upload PZ-format JSONs to a ParaTranz project.

Usage:
    PZ_TOKEN=xxx PZ_PROJECT_ID=12345 python3 scripts/upload_pz.py <pz_dir> [version_prefix]

Environment variables:
    PZ_TOKEN       - ParaTranz API token (required)
    PZ_PROJECT_ID  - ParaTranz project ID (required)
"""
import os, sys, json, time, glob, uuid
import urllib.request, urllib.error


def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
    with open(config_path) as f:
        return json.load(f)


def multipart_post(url, filename, filepath, path_value, token):
    boundary = uuid.uuid4().hex
    with open(filepath, 'rb') as f:
        file_data = f.read()

    ctype = 'multipart/form-data; boundary=' + boundary
    sep = ('--' + boundary).encode()

    parts = []
    parts.append(sep + b'\r\nContent-Disposition: form-data; name="path"\r\n\r\n' + path_value.encode() + b'\r\n')
    parts.append(sep + b'\r\nContent-Disposition: form-data; name="file"; filename="' + filename.encode() + b'"\r\nContent-Type: application/json\r\n\r\n' + file_data + b'\r\n')
    parts.append(sep + b'--\r\n')

    body = b''.join(parts)
    req = urllib.request.Request(url, data=body, method='POST', headers={
        'Authorization': 'Bearer ' + token,
        'Content-Type': ctype,
    })
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]


def upload(pz_dir, version_prefix, project_id, token):
    base = 'https://paratranz.cn/api'
    local_files = sorted(glob.glob(os.path.join(pz_dir, '**', '*.json'), recursive=True))
    print("Local files: {}".format(len(local_files)))

    ok = 0
    fail = 0
    for i, lf in enumerate(local_files):
        rel = os.path.relpath(lf, pz_dir)
        filename = os.path.basename(rel)
        dir_part = os.path.dirname(rel)
        if dir_part:
            path_value = version_prefix + '/' + dir_part + '/'
        else:
            path_value = version_prefix + '/'

        status, body = multipart_post(
            base + '/projects/' + str(project_id) + '/files',
            filename, lf, path_value, token
        )
        if status in (200, 201):
            ok += 1
        else:
            fail += 1
            if fail <= 5:
                print("  FAIL [{}] {} (path={}): {}".format(status, filename, path_value, str(body)[:100]))
        if (i + 1) % 50 == 0:
            print("  progress: {}/{} ok={}".format(i + 1, len(local_files), ok))
        time.sleep(0.15)

    print("\nDone: {}/{} ok, {} fail".format(ok, len(local_files), fail))


if __name__ == '__main__':
    token = os.environ.get('PZ_TOKEN')
    if not token:
        print('Error: PZ_TOKEN environment variable required', file=sys.stderr)
        sys.exit(1)

    project_id = os.environ.get('PZ_PROJECT_ID')
    if not project_id:
        print('Error: PZ_PROJECT_ID environment variable required', file=sys.stderr)
        sys.exit(1)

    config = load_config()
    pz_dir = sys.argv[1] if len(sys.argv) > 1 else 'pz_export'
    ver = sys.argv[2] if len(sys.argv) > 2 else config.get('source_version', '0.18')
    upload(pz_dir, ver, project_id, token)
