"""Record an explicit user decision about rendered page previews.

The command never infers approval from file existence or technical checks.
"""
import argparse
from studio import Project, read, sha, stamp, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--status", required=True, choices=["approved", "changes_requested", "rejected"])
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--notes", required=True)
    args = parser.parse_args()
    project = Project(args.project)
    manifest = read(project.file(args.manifest))
    if manifest.get("status") != "pending_user_review":
        raise ValueError("Preview manifest is not awaiting user review")
    previews = manifest.get("previews")
    if not isinstance(previews, list) or not previews:
        raise ValueError("Preview manifest has no pages")
    files = {}
    for row in previews:
        path = row.get("path")
        if not path:
            raise ValueError("Preview row has no path")
        file = project.file(path)
        if not file.is_file() or sha(file) != row.get("sha256"):
            raise ValueError("Preview changed; regenerate and show a new manifest: " + path)
        files[path] = row["sha256"]
    reviewer = args.reviewer.strip()
    notes = args.notes.strip()
    if not reviewer or not notes:
        raise ValueError("Reviewer and notes are required")
    rel = ".history/user-design-review-" + stamp() + ".json"
    manifest["user_review"] = rel
    manifest["status"] = "reviewed"
    write(project.file(args.manifest), manifest)
    report = {
        "manifest": args.manifest,
        "manifest_sha256": sha(project.file(args.manifest)),
        "status": args.status,
        "reviewer": reviewer,
        "notes": notes,
        "files": files,
        "previews": previews,
        "technical_checks": "separate from user visual decision",
    }
    write(project.file(rel), report)
    for scene in project.data["scenes"]:
        if scene.get("design_preview_manifest") == args.manifest:
            scene["user_design_review"] = rel
    write(project.file("project.json"), project.data)
    project.save("user_design_review_recorded", report=rel, status=args.status)
    print(rel)


if __name__ == "__main__":
    main()
