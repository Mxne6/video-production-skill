#!/usr/bin/env python3
"""Validate the video scene visual contract without changing project approvals."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RATIOS = {
    "3:4": (1080, 1440),
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "4:3": (1440, 1080),
}
THEMES = {
    "editorial": {"ink-classic", "indigo-porcelain", "forest-ink", "kraft-paper", "dune", "midnight-ink"},
    "swiss": {"ikb", "lemon-yellow", "lemon-green", "safety-orange"},
}
MOTIONS = {"static", "fade-in", "slow-pan", "slow-zoom", "line-reveal", "step-reveal", "number-count"}
ROLES = {"cover", "statement", "evidence", "comparison", "process", "recap", "outro"}
RECIPES = {
    "editorial": re.compile(r"^M(?:0[1-9]|1[0-6])(?:-video)?$"),
    "swiss": re.compile(r"^S(?:0[1-9]|1[0-2])(?:-video)?$"),
}
REQUIRED = ("scene_id", "role", "duration_seconds", "ratio", "style_mode", "theme", "recipe", "motion", "subtitle_safe_area", "visual_intent")


def validate_scene(scene: dict, index: int) -> list[str]:
    errors = []
    prefix = f"scene[{index}]"
    missing = [key for key in REQUIRED if key not in scene]
    errors.extend(f"{prefix}: missing {key}" for key in missing)
    if missing:
        return errors
    if not isinstance(scene["scene_id"], str) or not re.fullmatch(r"[A-Za-z0-9_-]+", scene["scene_id"]):
        errors.append(f"{prefix}: scene_id must use letters, numbers, underscore or hyphen")
    if scene["role"] not in ROLES:
        errors.append(f"{prefix}: unsupported role {scene['role']!r}")
    if scene["ratio"] not in RATIOS:
        errors.append(f"{prefix}: unsupported ratio {scene['ratio']!r}")
    style = scene["style_mode"]
    if style not in THEMES:
        errors.append(f"{prefix}: style_mode must be editorial or swiss")
    elif scene["theme"] not in THEMES[style]:
        errors.append(f"{prefix}: theme {scene['theme']!r} does not belong to {style}")
    if style in RECIPES and not RECIPES[style].fullmatch(str(scene["recipe"])):
        errors.append(f"{prefix}: recipe {scene['recipe']!r} does not belong to {style}")
    if scene["motion"] not in MOTIONS:
        errors.append(f"{prefix}: unsupported motion {scene['motion']!r}")
    if not isinstance(scene["duration_seconds"], (int, float)) or scene["duration_seconds"] <= 0:
        errors.append(f"{prefix}: duration_seconds must be positive")
    if not isinstance(scene["visual_intent"], str) or not scene["visual_intent"].strip():
        errors.append(f"{prefix}: visual_intent must be non-empty")
    if not isinstance(scene["subtitle_safe_area"], str) or not scene["subtitle_safe_area"].strip():
        errors.append(f"{prefix}: subtitle_safe_area must be non-empty")
    media = scene.get("media", [])
    if media is not None and not isinstance(media, list):
        errors.append(f"{prefix}: media must be a list when present")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--expected-ratio", choices=sorted(RATIOS))
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    scenes = data.get("scenes") if isinstance(data, dict) and "scenes" in data else data
    if isinstance(scenes, dict):
        scenes = [scenes]
    if not isinstance(scenes, list) or not scenes:
        raise SystemExit("BLOCKED: manifest must contain one scene object or a non-empty scenes list")
    errors = []
    ids = set()
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            errors.append(f"scene[{index}]: must be an object")
            continue
        errors.extend(validate_scene(scene, index))
        scene_id = scene.get("scene_id")
        if scene_id in ids:
            errors.append(f"scene[{index}]: duplicate scene_id {scene_id!r}")
        ids.add(scene_id)
        if args.expected_ratio and scene.get("ratio") != args.expected_ratio:
            errors.append(f"scene[{index}]: expected ratio {args.expected_ratio}, got {scene.get('ratio')}")
    report = {"status": "pass" if not errors else "fail", "scene_count": len(scenes), "errors": errors,
              "expected_ratio": args.expected_ratio, "technical_only": True}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if errors:
        for error in errors:
            print("FAIL: " + error)
        return 1
    print(f"PASS: {len(scenes)} scene contract(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
