"""Collect finished page PNGs for explicit user visual review.

This command never marks a design as approved. It creates a manifest, prints
absolute image paths and Markdown embeds, and records which files were shown.
"""
import argparse
import json
from pathlib import Path
from studio import Project, sha, stamp, write


def candidates(project, scene):
    explicit = scene.get("preview_png") or scene.get("design_png")
    values = []
    if explicit:
        values.append(project.file(explicit))
    values.extend([
        project.path / "design" / scene["id"] / "output.png",
        project.path / "scenes" / scene["id"] / "output.png",
    ])
    html = scene.get("html")
    if html:
        values.append(project.file(html).parent / "output.png")
    seen = set()
    return [p for p in values if not (str(p) in seen or seen.add(str(p)))]


def collect(project, selected):
    rows = []
    for scene in project.scenes(selected):
        png = next((p for p in candidates(project, scene) if p.is_file()), None)
        if png is None:
            raise ValueError(scene["id"] + ": rendered PNG not found; render the page before showing it")
        if not png.resolve().is_relative_to(project.path):
            raise ValueError(scene["id"] + ": preview escapes project root")
        rel = png.relative_to(project.path).as_posix()
        absolute = str(png.resolve())
        rows.append({
            "scene": scene["id"],
            "path": rel,
            "absolute_path": absolute,
            "sha256": sha(png),
            "markdown": f"![{scene['id']}]({absolute.replace(chr(92), '/')})",
            "status": "shown_pending_user_review",
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project")
    parser.add_argument("--scenes", default="all")
    args = parser.parse_args()
    project = Project(args.project)
    previews = collect(project, args.scenes)
    manifest = {
        "status": "pending_user_review",
        "created_at": stamp(),
        "project": str(project.path),
        "previews": previews,
        "user_review": None,
        "note": "Technical listing only; showing an image does not imply user approval.",
    }
    rel = "review/design-previews-" + stamp() + ".json"
    manifest["manifest_path"] = rel
    write(project.file(rel), manifest)
    for scene, row in zip(project.scenes(args.scenes), previews):
        scene["design_preview_manifest"] = rel
    write(project.file("project.json"), project.data)
    project.save("design_previews_prepared", manifest=rel, scenes=[x["scene"] for x in previews])
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
