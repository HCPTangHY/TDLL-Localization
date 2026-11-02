#!/usr/bin/env python3
"""Overwrite existing files on ParaTranz project with latest PZ-format JSONs.

Usage:
    PZ_TOKEN=xxx python3 scripts/overwrite_pz.py <pz_dir> [version_prefix]

Compares local files against remote, updates existing (POST /files/{id})
and creates new ones.
"""
import os, sys, json, time, glob, uuid
import urllib.request, urllib.error


def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
    with open(config_path) as f:
        return json.load(f)


def api_get(path, token):
    base = 'https://paratranz.cn/api'
    req = urllib.request.Request(base + path, headers={'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def multipart_post(url, filename, filepath, token, path_value=None):
    boundary = uuid.uuid4().hex
    body = b''
    if path_value:
        body += ('--' + boundary + '\r\nContent-Disposition: form-data; name="path"\r\n\r\n' + path_value + '\r\n').encode()
    body += ('--' + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="' + filename + '"\r\nContent-Type: application/json\r\n\r\n').encode()
    with open(filepath, 'rb') as f:
        body += f.read()
    body += ('\r\n--' + boundary + '--\r\n').encode()
    req = urllib.request.Request(url, data=body, method='POST', headers={
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'multipart/form-data; boundary=' + boundary,
    })
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def main():
    token = os.environ.get('PZ_TOKEN')
    if not token:
        print('Error: PZ_TOKEN environment variable required', file=sys.stderr)
        sys.exit(1)

    config = load_config()
    project_id = config['pz_project_id']
    base = 'https://paratranz.cn/api'

    pz_dir = sys.argv[1] if len(sys.argv) > 1 else 'pz_export'
    ver = sys.argv[2] if len(sys.argv) > 2 else config.get('source_version', '0.18')

    pz_files = api_get('/projects/' + str(project_id) + '/files', token)
    pz_map = {f['name']: f['id'] for f in pz_files}
    print('PZ existing: ' + str(len(pz_map)))

    local_files = sorted(glob.glob(os.path.join(pz_dir, '**', '*.json'), recursive=True))
    print('Local: ' + str(len(local_files)))

    ok = 0; fail = 0; created = 0; updated = 0
    for i, lf in enumerate(local_files):
        rel = os.path.relpath(lf, pz_dir)
        filename = os.path.basename(rel)
        rel_dir = os.path.dirname(rel)
        folder = ver + '/' + rel_dir if rel_dir else ver
        pz_name = folder + '/' + filename

        if pz_name in pz_map:
            fid = pz_map[pz_name]
            status = multipart_post(base + '/projects/' + str(project_id) + '/files/' + str(fid), filename, lf, token)
            if status in (200, 201):
                updated += 1
        else:
            status = multipart_post(base + '/projects/' + str(project_id) + '/files', filename, lf, token, path_value=folder)
            if status in (200, 201):
                created += 1

        if status in (200, 201):
            ok += 1
        else:
            fail += 1
            if fail <= 5:
                print('  FAIL [{}] {}'.format(status, pz_name))
        if (i + 1) % 50 == 0:
            print('  progress: {}/{} ok={}'.format(i + 1, len(local_files), ok))
        time.sleep(0.15)

    print('\nDone: {}/{} ok ({} updated, {} created), {} fail'.format(ok, len(local_files), updated, created, fail))

if __name__ == '__main__':
    main()
