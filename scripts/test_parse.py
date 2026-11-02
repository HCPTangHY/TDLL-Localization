#!/usr/bin/env python3
"""Quick self-check for parse.py — run after changes to verify nothing broke."""
import os, sys

scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from parse import parse_scene, rebuild_scene, flatten_json, apply_json_translations
import json

# ── scene round-trip ──
SAMPLE_SCENE = """\
[name] Study with Miran
[cast a=Hero, m=Miran]
You spend the evening studying.

[if room-open(m)]
    [show portrait m blushing]
    m: That was fun... um, do you want to come over?
    hint: You can visit Miran's room.
[else]
    m: Thanks for studying with me.

[stop mood-song]
"""

entries = parse_scene(SAMPLE_SCENE, 'test')
assert len(entries) == 6, "Expected 6 entries, got {}".format(len(entries))
assert entries[0]['key'].startswith('name:'), entries[0]['key']
assert 'Study with Miran' in entries[0]['original']

# Round-trip: translate one entry, rebuild, check it appears
translations = {entries[2]['key']: '好有趣……你要不要来我房间？'}
rebuilt = rebuild_scene(SAMPLE_SCENE, translations)
assert '好有趣' in rebuilt, "Translation not found in rebuilt scene"
assert '[cast a=Hero, m=Miran]' in rebuilt, "Bracket command corrupted"
assert '[show portrait m blushing]' in rebuilt, "Show command corrupted"

# ── JSON round-trip ──
sample_json = '{"a": {"b": "hello", "c": "world"}, "d": "test"}'
data = json.loads(sample_json)
flat = flatten_json(data, sample_json)
assert len(flat) == 3
assert flat[0]['key'] == 'a.b'
assert flat[0]['original'] == 'hello'

result = apply_json_translations(data, {'a.b': '你好'})
assert result['a']['b'] == '你好'
assert result['a']['c'] == 'world'

print("All checks passed.")
