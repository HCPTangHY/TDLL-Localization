#!/usr/bin/env python3
"""Build a TDLL translation pack from ParaTranz-exported JSON files.

Reads PZ-format JSONs (list of {key, original, translation, context}) and the
English source pack, produces a game-ready translation folder and zip.

Usage:
    python3 scripts/build_pack.py \
        --pz-dir   pz_export/          \
        --source   upstream/0.18/source \
        --config   config.json          \
        --out      build/

The output zip can be imported directly in-game via Settings -> Translations.
"""
import argparse
import json
import os
import sys
import zipfile
from pathlib import Path

# Allow importing parse.py from the same directory
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from parse import (
    parse_scene, rebuild_scene,
    flatten_json, apply_json_translations,
    GRAMMAR_SKIP_KEYS,
)


def load_pz_translations(path):
    """Load a PZ JSON file and return {key: translation} for non-empty entries."""
    with open(path, encoding="utf-8") as f:
        entries = json.load(f)
    return {
        e["key"]: e["translation"]
        for e in entries
        if e.get("translation", "").strip()
    }


def find_pz_root(pz_dir):
    """Auto-detect version prefix in PZ artifact.

    PZ uploads use a version prefix (e.g. '0.18/'), so the artifact
    structure is pz_dir/0.18/strings.json. We detect and return the
    actual root containing strings.json and scenes/.
    """
    pz_dir = Path(pz_dir)

    # Direct structure: pz_dir/strings.json
    if (pz_dir / "strings.json").exists():
        return pz_dir

    # Version-prefixed: pz_dir/0.18/strings.json
    for child in sorted(pz_dir.iterdir()):
        if child.is_dir() and (child / "strings.json").exists():
            print("  detected PZ version prefix: {}/".format(child.name))
            return child

    # Deeper nesting: pz_dir/utf8/0.18/strings.json (PZ artifact quirk)
    for root, dirs, files in os.walk(pz_dir):
        if "strings.json" in files:
            found = Path(root)
            print("  detected PZ root at: {}".format(found.relative_to(pz_dir)))
            return found

    print("  WARNING: could not find strings.json in PZ directory", file=sys.stderr)
    return pz_dir


# ---------------------------------------------------------------------------
# strings.json
# ---------------------------------------------------------------------------

def build_strings(pz_translations, source_path, out_path):
    """Build translated strings.json using PZ translations + English source."""
    with open(source_path, encoding="utf-8") as f:
        source = json.load(f)

    result = apply_json_translations(source, pz_translations)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return len(pz_translations)


# ---------------------------------------------------------------------------
# grammar.json
# ---------------------------------------------------------------------------

def build_grammar(pz_translations, source_path, out_path):
    """Build translated grammar.json using PZ translations + English source."""
    with open(source_path, encoding="utf-8") as f:
        source = json.load(f)

    result = apply_json_translations(source, pz_translations)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return len(pz_translations)


# ---------------------------------------------------------------------------
# scenes — POS-based rebuild via parse.py
# ---------------------------------------------------------------------------

def build_scenes(pz_scenes_dir, source_scenes_dir, out_scenes_dir):
    """Rebuild all .scene files using POS-based splicing from parse.py."""
    pz_scenes_dir = Path(pz_scenes_dir)
    source_scenes_dir = Path(source_scenes_dir)
    out_scenes_dir = Path(out_scenes_dir)

    if not pz_scenes_dir.exists():
        print("  WARNING: no scenes/ in PZ export", file=sys.stderr)
        return 0, 0

    scene_count = 0
    translated_count = 0

    for pz_json in sorted(pz_scenes_dir.rglob("*.json")):
        rel_json = pz_json.relative_to(pz_scenes_dir)
        scene_rel = str(rel_json).replace(".json", ".scene")
        src_scene = source_scenes_dir / scene_rel

        if not src_scene.exists():
            continue

        # Load PZ translations
        translations = load_pz_translations(pz_json)

        # Read English source scene
        source_text = src_scene.read_text("utf-8")

        # POS-based rebuild
        translated_text = rebuild_scene(source_text, translations)

        # Write output
        out_scene = out_scenes_dir / scene_rel
        out_scene.parent.mkdir(parents=True, exist_ok=True)
        out_scene.write_text(translated_text, "utf-8")

        scene_count += 1
        if translations:
            translated_count += 1

    return scene_count, translated_count


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------

def compute_coverage(pz_root):
    """Count total and translated entries across all PZ JSONs."""
    total = 0
    translated = 0
    for root, _, files in os.walk(pz_root):
        for fn in files:
            if not fn.endswith(".json"):
                continue
            with open(os.path.join(root, fn), encoding="utf-8") as f:
                entries = json.load(f)
            total += len(entries)
            translated += sum(1 for e in entries if e.get("translation", "").strip())
    pct = round(translated / total * 100, 1) if total else 0
    return total, translated, pct


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_pack(pz_dir, source_dir, config, out_dir):
    pack_code = config["pack_code"]
    pack_dir = out_dir / pack_code
    pack_dir.mkdir(parents=True, exist_ok=True)

    # Auto-detect version prefix in PZ artifact
    pz_root = find_pz_root(pz_dir)

    # --- manifest.json ---
    manifest = {
        "code": pack_code,
        "language": config["pack_language"],
        "name": config["pack_name"],
        "description": config["pack_description"],
        "version": config["game_version"],
    }
    with open(pack_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # --- strings.json ---
    pz_strings_path = pz_root / "strings.json"
    if pz_strings_path.exists():
        pz_strings = load_pz_translations(pz_strings_path)
        n = build_strings(pz_strings, source_dir / "strings.json", pack_dir / "strings.json")
        print("  strings.json: {} translated entries".format(n))
    else:
        print("  WARNING: strings.json not found in PZ export", file=sys.stderr)

    # --- grammar.json ---
    pz_grammar_path = pz_root / "grammar.json"
    if pz_grammar_path.exists():
        pz_grammar = load_pz_translations(pz_grammar_path)
        n = build_grammar(pz_grammar, source_dir / "grammar.json", pack_dir / "grammar.json")
        print("  grammar.json: {} translated entries".format(n))
    else:
        print("  WARNING: grammar.json not found in PZ export", file=sys.stderr)

    # --- scenes ---
    scene_total, scene_translated = build_scenes(
        pz_root / "scenes",
        source_dir / "scenes",
        pack_dir / "scenes",
    )
    print("  scenes: {} total, {} with translations".format(scene_total, scene_translated))

    # --- coverage ---
    total, translated, pct = compute_coverage(pz_root)
    print("  coverage: {}/{} ({}%)".format(translated, total, pct))

    # --- zip ---
    zip_path = out_dir / "{}.zip".format(pack_code)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(pack_dir):
            for fn in files:
                fp = Path(root) / fn
                arcname = fp.relative_to(out_dir).as_posix()
                zf.write(fp, arcname)
    print("  zip: {} ({} KB)".format(zip_path.name, zip_path.stat().st_size // 1024))

    return zip_path


def main():
    parser = argparse.ArgumentParser(description="Build TDLL translation pack from PZ export")
    parser.add_argument("--pz-dir", required=True, help="Directory with PZ-exported JSON files")
    parser.add_argument("--source", required=True, help="English source pack directory")
    parser.add_argument("--config", required=True, help="config.json path")
    parser.add_argument("--out", default="build", help="Output directory")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        config = json.load(f)

    print("Building pack: {}".format(config["pack_code"]))
    build_pack(
        pz_dir=Path(args.pz_dir),
        source_dir=Path(args.source),
        config=config,
        out_dir=Path(args.out),
    )
    print("Done!")


if __name__ == "__main__":
    main()
