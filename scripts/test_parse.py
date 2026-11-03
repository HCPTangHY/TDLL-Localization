#!/usr/bin/env python3
"""Quick self-check for parse.py."""
import os, sys

scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from parse import parse_scene, rebuild_scene, flatten_json, apply_json_translations, KEY_SEP
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

translations = {entries[2]['key']: '好有趣……你要不要来我房间？'}
rebuilt = rebuild_scene(SAMPLE_SCENE, translations)
assert '好有趣' in rebuilt
assert '[cast a=Hero, m=Miran]' in rebuilt

# ── JSON round-trip with | separator ──
sample_json = '{"a": {"b": "hello", "c": "world"}, "d": "test"}'
data = json.loads(sample_json)
flat = flatten_json(data, sample_json)
assert len(flat) == 3
assert flat[0]['key'] == 'a' + KEY_SEP + 'b', 'Got: ' + flat[0]['key']
assert flat[0]['original'] == 'hello'

result = apply_json_translations(data, {'a' + KEY_SEP + 'b': '你好'})
assert result['a']['b'] == '你好'
assert result['a']['c'] == 'world'

# ── dotted dict keys (grammar.json pattern) ──
grammar_sample = '{"nouns": {"items.armor.cloak": {"base": "cloak", "definite": "the cloak"}}}'
gdata = json.loads(grammar_sample)
gflat = flatten_json(gdata, grammar_sample)

# Should produce nouns|items.armor.cloak|base  (dots preserved in dict key)
assert len(gflat) == 2
assert gflat[0]['key'] == 'nouns' + KEY_SEP + 'items.armor.cloak' + KEY_SEP + 'base'
assert gflat[0]['original'] == 'cloak'

# Apply translation
gresult = apply_json_translations(gdata, {'nouns|items.armor.cloak|base': '斗篷'})
assert gresult['nouns']['items.armor.cloak']['base'] == '斗篷'
assert gresult['nouns']['items.armor.cloak']['definite'] == 'the cloak'

print("All checks passed.")
