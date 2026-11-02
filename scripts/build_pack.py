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
import re
import sys
import zipfile
from pathlib import Path


def load_pz_file(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_all_pz(pz_dir):
    """Load all PZ JSON files into {relative_path: {key: translation}}."""
    result = {}
    for root, _, files in os.walk(pz_dir):
        for fn in files:
            if not fn.endswith(".json"):
                continue
            fp = Path(root) / fn
            rel = fp.relative_to(pz_dir).as_posix()
            entries = load_pz_file(fp)
            translations = {}
            for e in entries:
                t = e.get("translation", "").strip()
                if t:
                    translations[e["key"]] = t
            result[rel] = translations
    return result


# ---------------------------------------------------------------------------
# strings.json  (nested dict in source, PZ flat list)
# ---------------------------------------------------------------------------

def flatten_nested(d, prefix=""):
    """Flatten nested dict to {dotted.key: value}."""
    items = {}
    for k, v in d.items():
        key = "{}.{}".format(prefix, k) if prefix else k
        if isinstance(v, dict):
            items.update(flatten_nested(v, key))
        else:
            items[key] = v
    return items


def unflatten(flat):
    """Unflatten {dotted.key: value} back to nested dict."""
    root = {}
    for dotted_key, value in flat.items():
        parts = dotted_key.split(".")
        d = root
        for p in parts[:-1]:
            if p not in d:
                d[p] = {}
            d = d[p]
        d[parts[-1]] = value
    return root


def build_strings(pz_data, source):
    """Build translated strings.json from PZ translations + English source."""
    flat_source = flatten_nested(source)
    flat_out = {}
    for key, eng_val in flat_source.items():
        translated = pz_data.get(key, "")
        flat_out[key] = translated if translated else eng_val
    return unflatten(flat_out)


# ---------------------------------------------------------------------------
# grammar.json  (structured in source, PZ flat list)
# ---------------------------------------------------------------------------

def build_grammar(pz_data, source):
    """Build translated grammar.json."""
    out = {}

    # genders section
    if "genders" in source:
        out_genders = {}
        for gender_name, gender_forms in source["genders"].items():
            out_gender = {}
            for form, eng_val in gender_forms.items():
                pz_key = "genders.{}.{}".format(gender_name, form)
                translated = pz_data.get(pz_key, "")
                out_gender[form] = translated if translated else eng_val
            out_genders[gender_name] = out_gender
        out["genders"] = out_genders

    # nouns section
    if "nouns" in source:
        out_nouns = {}
        for noun_key, noun_data in source["nouns"].items():
            out_noun = {}
            for field, eng_val in noun_data.items():
                if isinstance(eng_val, str):
                    pz_key = "nouns.{}.{}".format(noun_key, field)
                    translated = pz_data.get(pz_key, "")
                    out_noun[field] = translated if translated else eng_val
                else:
                    # bool/int fields like plural, second_person
                    out_noun[field] = eng_val
            out_nouns[noun_key] = out_noun
        out["nouns"] = out_nouns

    # separators
    if "separators" in source:
        out_sep = {}
        for k, v in source["separators"].items():
            pz_key = "separators.{}".format(k)
            translated = pz_data.get(pz_key, "")
            out_sep[k] = translated if translated else v
        out["separators"] = out_sep

    return out


# ---------------------------------------------------------------------------
# scenes  (.scene files, PZ flat list per scene)
# ---------------------------------------------------------------------------

def parse_scene_translatable(text):
    """Parse a .scene file and extract translatable lines.

    Returns [(line_idx, indent, prefix, text), ...]
    """
    results = []
    for i, line in enumerate(text.split("\n")):
        stripped = line.lstrip()
        indent = line[: len(line) - len(stripped)]
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("["):
            if stripped.startswith("[name] "):
                results.append((i, indent, "[name] ", stripped[7:]))
            elif stripped.startswith("[blocker "):
                try:
                    bracket_end = stripped.index("]")
                    reason = stripped[bracket_end + 2:] if len(stripped) > bracket_end + 2 else ""
                    if reason:
                        bracket_part = stripped[:bracket_end + 1]
                        results.append((i, indent, bracket_part + " ", reason))
                except ValueError:
                    pass
            continue

        # hint: / flavor: lines
        handled = False
        for tag in ("hint:", "flavor:"):
            if stripped.startswith(tag):
                rest = stripped[len(tag):]
                results.append((i, indent, tag, rest.lstrip() if rest else ""))
                handled = True
                break
        if handled:
            continue

        # Speaker prefix
        m = re.match(r"^([a-zA-Z_]\w{0,15}:\s)", stripped)
        if m:
            results.append((i, indent, m.group(0), stripped[len(m.group(0)):]))
        else:
            # Plain narration / menu option
            results.append((i, indent, "", stripped))
    return results


def build_scene(pz_entries, source_text):
    """Rebuild a .scene file with translations injected."""
    lines = source_text.split("\n")
    translatable = parse_scene_translatable(source_text)

    if len(translatable) != len(pz_entries):
        # Mismatch -- return source unchanged (will play in English)
        print("    WARNING: PZ entry count mismatch ({} vs {}), skipping".format(
            len(translatable), len(pz_entries)), file=sys.stderr)
        return source_text

    for (line_idx, indent, prefix, _eng_text), pz_entry in zip(translatable, pz_entries):
        translated = pz_entry.get("translation", "").strip()
        if translated:
            lines[line_idx] = indent + prefix + translated

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Coverage stats
# ---------------------------------------------------------------------------

def compute_coverage(pz_dir):
    total = 0
    translated = 0
    for root, _, files in os.walk(pz_dir):
        for fn in files:
            if not fn.endswith(".json"):
                continue
            fp = Path(root) / fn
            entries = load_pz_file(fp)
            file_total = len(entries)
            file_translated = sum(1 for e in entries if e.get("translation", "").strip())
            total += file_total
            translated += file_translated
    pct = round(translated / total * 100, 1) if total else 0
    return {"total": total, "translated": translated, "percent": pct}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_pack(pz_dir, source_dir, config, out_dir):
    pack_code = config["pack_code"]
    pack_dir = out_dir / pack_code
    pack_dir.mkdir(parents=True, exist_ok=True)

    pz_all = load_all_pz(pz_dir)

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
    pz_strings = pz_all.get("strings.json", {})
    with open(source_dir / "strings.json", encoding="utf-8") as f:
        source_strings = json.load(f)
    translated_strings = build_strings(pz_strings, source_strings)
    with open(pack_dir / "strings.json", "w", encoding="utf-8") as f:
        json.dump(translated_strings, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("  strings.json: {} translated entries".format(len(pz_strings)))

    # --- grammar.json ---
    pz_grammar = pz_all.get("grammar.json", {})
    with open(source_dir / "grammar.json", encoding="utf-8") as f:
        source_grammar = json.load(f)
    translated_grammar = build_grammar(pz_grammar, source_grammar)
    with open(pack_dir / "grammar.json", "w", encoding="utf-8") as f:
        json.dump(translated_grammar, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("  grammar.json: {} translated entries".format(len(pz_grammar)))

    # --- scenes ---
    scene_count = 0
    translated_scene_count = 0
    for pz_rel in pz_all:
        if not pz_rel.startswith("scenes/"):
            continue
        scene_rel = pz_rel.replace(".json", ".scene")
        source_scene = source_dir / scene_rel
        if not source_scene.exists():
            continue

        pz_path = pz_dir / pz_rel
        pz_entries = load_pz_file(pz_path)

        with open(source_scene, encoding="utf-8") as f:
            source_text = f.read()

        translated_text = build_scene(pz_entries, source_text)
        out_scene = pack_dir / scene_rel
        out_scene.parent.mkdir(parents=True, exist_ok=True)
        with open(out_scene, "w", encoding="utf-8", newline="\n") as f:
            f.write(translated_text)

        scene_count += 1
        has_translation = any(e.get("translation", "").strip() for e in pz_entries)
        if has_translation:
            translated_scene_count += 1

    print("  scenes: {} total, {} with translations".format(scene_count, translated_scene_count))

    # --- coverage ---
    coverage = compute_coverage(pz_dir)
    print("  coverage: {}/{} ({}%)".format(
        coverage["translated"], coverage["total"], coverage["percent"]))

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
