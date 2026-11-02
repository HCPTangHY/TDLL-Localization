#!/usr/bin/env python3
"""TDLL <-> PZ format converter.

source pack -> pz_origin: entries with key (fingerprint) + context (<<POS:offset>>)
pz_translated -> author pack: POS-based sequential splicing rebuild

Usage:
    python3 scripts/convert.py to-pz <source_dir> <out_dir>
    python3 scripts/convert.py to-pack <source_dir> <pz_dir> <out_dir> <manifest.json>
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Allow running from scripts/ dir or repo root
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from parse import (
    flatten_json, apply_json_translations,
    parse_scene, rebuild_scene,
    GRAMMAR_SKIP_KEYS,
)


# ── source -> PZ ──────────────────────────────────────────────────────

def pack_to_pz(source_dir, out_dir):
    # type: (str, str) -> None
    src = Path(source_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stats = {'files': 0, 'entries': 0}

    _convert_json_file(src / 'strings.json', out / 'strings.json', stats)
    _convert_json_file(
        src / 'grammar.json', out / 'grammar.json', stats,
        skip_keys=GRAMMAR_SKIP_KEYS,
    )

    scenes_src = src / 'scenes'
    scenes_out = out / 'scenes'
    for scene_path in sorted(scenes_src.rglob('*.scene')):
        rel = scene_path.relative_to(scenes_src)
        scene_id = str(rel).replace('.scene', '').replace('\\', '/')
        json_name = str(rel).replace('.scene', '.json')
        dst = scenes_out / json_name
        dst.parent.mkdir(parents=True, exist_ok=True)

        source_text = scene_path.read_text('utf-8')
        entries = parse_scene(source_text, scene_id)
        if not entries:
            continue

        pz_data = _entries_to_pz(entries)
        dst.write_text(json.dumps(pz_data, ensure_ascii=False, indent=2), 'utf-8')
        stats['files'] += 1
        stats['entries'] += len(entries)

    print("Done: {} files, {} entries".format(stats['files'], stats['entries']))


def _convert_json_file(src_path, dst_path, stats, skip_keys=frozenset()):
    if not src_path.exists():
        return
    raw_text = src_path.read_text('utf-8')
    data = json.loads(raw_text)
    entries = flatten_json(data, raw_text, skip_keys)
    if not entries:
        return
    pz_data = [
        {'key': e['key'], 'original': e['original'], 'translation': '', 'context': e.get('context', '')}
        for e in entries
    ]
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    dst_path.write_text(json.dumps(pz_data, ensure_ascii=False, indent=2), 'utf-8')
    stats['files'] += 1
    stats['entries'] += len(entries)


def _entries_to_pz(entries):
    # type: (list) -> list
    return [
        {
            'key': e['key'],
            'original': e['translation_original'],
            'translation': '',
            'context': e.get('context', ''),
        }
        for e in entries
    ]


# ── PZ -> author pack ─────────────────────────────────────────────────

def pz_to_pack(source_dir, pz_dir, out_dir, manifest):
    # type: (str, str, str, dict) -> None
    src = Path(source_dir)
    pz  = Path(pz_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    (out / 'manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), 'utf-8',
    )

    _rebuild_json(src / 'strings.json', pz / 'strings.json', out / 'strings.json')
    _rebuild_json(src / 'grammar.json', pz / 'grammar.json', out / 'grammar.json')

    # scenes: POS-based rebuild
    scenes_src = src / 'scenes'
    scenes_pz = pz / 'scenes'
    if not scenes_pz.exists():
        return

    for pz_json in sorted(scenes_pz.rglob('*.json')):
        rel_json = pz_json.relative_to(scenes_pz)
        scene_rel = str(rel_json).replace('.json', '.scene')
        src_scene = scenes_src / scene_rel
        if not src_scene.exists():
            print("WARN: source scene missing for {}".format(rel_json))
            continue

        with open(str(pz_json), 'r', encoding='utf-8') as f:
            pz_entries = json.load(f)

        translations = {
            e['key']: e['translation']
            for e in pz_entries
            if e.get('translation')
        }

        source_text = src_scene.read_text('utf-8')
        translated = rebuild_scene(source_text, translations)

        out_scene = out / 'scenes' / scene_rel
        out_scene.parent.mkdir(parents=True, exist_ok=True)
        out_scene.write_text(translated, 'utf-8')


def _rebuild_json(src_path, pz_path, out_path):
    if not src_path.exists():
        return
    with open(str(src_path), 'r', encoding='utf-8') as f:
        source = json.load(f)
    translations = {}
    if pz_path.exists():
        with open(str(pz_path), 'r', encoding='utf-8') as f:
            pz_entries = json.load(f)
        translations = {
            e['key']: e['translation']
            for e in pz_entries
            if e.get('translation')
        }
    result = apply_json_translations(source, translations)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf-8')


# ── CLI ───────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 scripts/convert.py to-pz <source_dir> <out_dir>")
        print("  python3 scripts/convert.py to-pack <source_dir> <pz_dir> <out_dir> <manifest.json>")
        return 1
    cmd = sys.argv[1]
    if cmd == 'to-pz':
        pack_to_pz(sys.argv[2], sys.argv[3])
    elif cmd == 'to-pack':
        with open(sys.argv[5], 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        pz_to_pack(sys.argv[2], sys.argv[3], sys.argv[4], manifest)
    else:
        print("Unknown command: {}".format(cmd))
        return 1

if __name__ == '__main__':
    sys.exit(main() or 0)
