#!/usr/bin/env python3
"""TDLL translation pack parser.

Key: content fingerprint (stable across versions if text unchanged) — for PZ identity.
POS: character offset in source file (stored in context as <<POS:xxx>>) — for rebuild.

Scene rebuild uses POS-based sequential splicing, same as TiTS/CoT replacers.
"""
from __future__ import annotations

import re
import copy
import json
import hashlib
from typing import Dict, FrozenSet, List, Optional, Set

# ── regex ────────────────────────────────────────────────────────────────────
_CAST_RE         = re.compile(r'^\s*\[cast\s+(.+?)\]\s*$')
_NAME_RE         = re.compile(r'^(\s*)\[name\]\s+(.+)$')
_BLOCKER_RE      = re.compile(r'^(\s*)\[blocker\s+[^\]]*?\]\s+(.+)$')
_SPEAKER_RE      = re.compile(r'^(\s*)([a-z][a-z0-9_]*):\s(.*)$')
_HINT_FLAVOR_RE  = re.compile(r'^(\s*)(hint|flavor):\s(.*)$')
_TRANSLATE_RE    = re.compile(r'\[TRANSLATE(?:[^\]]*)]\s*')
_COMMENT_RE      = re.compile(r'^\s*#\s*translator-note:')
GRAMMAR_SKIP_KEYS = frozenset({'gender'})


# ── fingerprint ───────────────────────────────────────────────────────────

def _sanitize_key(text):
    # type: (str) -> str
    t = text.lower()
    t = re.sub(r'[^a-z0-9]', '_', t)
    t = re.sub(r'_+', '_', t).strip('_')
    return t


def _generate_fingerprint(text, max_length=50):
    # type: (str, int) -> str
    cleaned = re.sub(r'\{[^}]*\}', '', text)
    cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)
    fp = _sanitize_key(cleaned)
    if len(fp) > max_length:
        fp = fp[:max_length].rstrip('_')
    if not fp:
        fp = 'h_' + hashlib.sha1(text.encode('utf-8')).hexdigest()[:8]
    return fp


# ── helpers ────────────────────────────────────────────────────────────────

def strip_marker(text):
    # type: (str) -> str
    return _TRANSLATE_RE.sub('', text).strip()


def _collect_speakers(lines):
    # type: (list) -> set
    speakers = set()  # type: Set[str]
    for raw in lines:
        m = _CAST_RE.match(raw.rstrip())
        if not m:
            continue
        for pair in m.group(1).split(','):
            p = pair.strip()
            if '=' in p:
                speakers.add(p.split('=', 1)[0].strip())
    return speakers


def _make_unique_key(entry_type, text, used_keys):
    # type: (str, str, dict) -> str
    fp = _generate_fingerprint(text)
    base = '{}:{}'.format(entry_type, fp)
    if base not in used_keys:
        used_keys[base] = 1
        return base
    fp_long = _generate_fingerprint(text, 80)
    base_long = '{}:{}'.format(entry_type, fp_long)
    if base_long not in used_keys:
        used_keys[base_long] = 1
        return base_long
    used_keys[base_long] = used_keys.get(base_long, 1) + 1
    return '{}_{}'.format(base_long, used_keys[base_long])


# ── scene parsing ───────────────────────────────────────────────────────────

def parse_scene(text, scene_id=''):
    # type: (str, str) -> list
    """Extract translatable entries from a .scene file.

    Returns [{key, original, context, pos}, ...].
    key = type:fingerprint (for PZ identity).
    pos = character offset of the translatable text in source (for rebuild).
    context includes <<POS:pos>> for replacer compatibility.
    """
    lines = text.split('\n')
    speakers = _collect_speakers(lines)
    entries = []  # type: list
    used_keys = {}  # type: Dict[str, int]

    # pre-compute line start offsets
    line_starts = []  # type: List[int]
    offset = 0
    for line in lines:
        line_starts.append(offset)
        offset += len(line) + 1  # +1 for \n

    for i, raw in enumerate(lines):
        line = raw.rstrip('\r\n')
        stripped = line.lstrip()
        line_offset = line_starts[i]

        if not stripped or _COMMENT_RE.match(line):
            continue

        # [name] Title
        m = _NAME_RE.match(line)
        if m:
            original = strip_marker(m.group(2))
            if original:
                pos = line_offset + line.index(m.group(2))
                key = _make_unique_key('name', original, used_keys)
                entries.append({
                    'key': key, 'original': m.group(2),
                    'translation_original': original,
                    'context': '<<POS:{:08d}>>'.format(pos),
                    'pos': pos,
                })
            continue

        # [blocker ...] Reason
        m = _BLOCKER_RE.match(line)
        if m:
            original = strip_marker(m.group(2))
            if original:
                pos = line_offset + line.index(m.group(2))
                key = _make_unique_key('blocker', original, used_keys)
                entries.append({
                    'key': key, 'original': m.group(2),
                    'translation_original': original,
                    'context': '<<POS:{:08d}>>'.format(pos),
                    'pos': pos,
                })
            continue

        # Bracket-only commands -> skip
        if stripped.startswith('['):
            continue

        # hint: / flavor:
        m = _HINT_FLAVOR_RE.match(line)
        if m:
            original = strip_marker(m.group(3))
            if original:
                pos = line_offset + line.index(m.group(3))
                key = _make_unique_key(m.group(2), original, used_keys)
                entries.append({
                    'key': key, 'original': m.group(3),
                    'translation_original': original,
                    'context': '<<POS:{:08d}>>'.format(pos),
                    'pos': pos,
                })
            continue

        # Speaker dialogue
        m = _SPEAKER_RE.match(line)
        if m and m.group(2) in speakers:
            original = strip_marker(m.group(3))
            speaker = m.group(2)
            if original:
                pos = line_offset + line.index(m.group(3))
                key = _make_unique_key(speaker, original, used_keys)
                entries.append({
                    'key': key, 'original': m.group(3),
                    'translation_original': original,
                    'context': '<<POS:{:08d}>>'.format(pos),
                    'pos': pos,
                })
            continue

        # Narration / menu option
        original = strip_marker(stripped)
        if original:
            leading = len(line) - len(stripped)
            pos = line_offset + leading
            key = _make_unique_key('narration', original, used_keys)
            entries.append({
                'key': key, 'original': stripped,
                'translation_original': original,
                'context': '<<POS:{:08d}>>'.format(pos),
                'pos': pos,
            })

    return entries


def rebuild_scene(source_text, translations):
    # type: (str, dict) -> str
    """POS-based sequential splicing, same as TiTS/CoT replacers.

    source_text:  English .scene content
    translations: {key: translated_text}  -- from PZ download

    We re-parse the source to get (key, pos, original_len), then splice.
    """
    entries = parse_scene(source_text)

    # Build splice list: (pos, original_raw, translation)
    items = []
    for e in entries:
        t = translations.get(e['key'])
        if t:
            items.append((e['pos'], e['original'], t))

    if not items:
        return source_text

    # Sort by pos ascending
    items.sort(key=lambda x: x[0])

    # Sequential splice
    parts = []
    last = 0
    for pos, orig_raw, trans in items:
        if pos < last:
            continue  # overlap, skip
        parts.append(source_text[last:pos])
        parts.append(trans)
        last = pos + len(orig_raw)

    parts.append(source_text[last:])
    return ''.join(parts)


# ── JSON (unchanged) ──────────────────────────────────────────────────────

def flatten_json(data, raw_text, skip_keys=frozenset()):
    # type: (dict, str, frozenset) -> list
    """Flatten nested JSON. raw_text is the original file content for POS lookup."""
    entries = []  # type: list
    _search_start = [0]  # mutable cursor for sequential POS search

    def _find_pos(value):
        # type: (str) -> int
        needle = json.dumps(value, ensure_ascii=False)[1:-1]
        idx = raw_text.find('"' + needle + '"', _search_start[0])
        if idx >= 0:
            pos = idx + 1
            _search_start[0] = idx + len(needle) + 2
            return pos
        return -1

    def walk(obj, path):
        if isinstance(obj, dict):
            for k in obj:
                walk(obj[k], '{}.{}'.format(path, k) if path else k)
        elif isinstance(obj, str):
            leaf = path.rsplit('.', 1)[-1] if '.' in path else path
            if leaf in skip_keys:
                return
            t = strip_marker(obj) if '[TRANSLATE' in obj else obj
            pos = _find_pos(obj)
            ctx = '<<POS:{:08d}>>'.format(pos) if pos >= 0 else ''
            entries.append({'key': path, 'original': t, 'context': ctx})

    walk(data, '')
    return entries


def apply_json_translations(source, translations):
    # type: (dict, dict) -> dict
    result = copy.deepcopy(source)
    for dotted, text in translations.items():
        parts = dotted.split('.')
        d = result
        try:
            for p in parts[:-1]:
                d = d[p]
            if parts[-1] in d and isinstance(d[parts[-1]], str):
                d[parts[-1]] = text
        except (KeyError, TypeError):
            pass
    return result
