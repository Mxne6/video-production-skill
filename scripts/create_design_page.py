"""Copy an upstream design seed into a project; create no review or approval."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

DESIGN = Path(__file__).resolve().parents[1] / 'design/guizang-social-card'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_page(project, scene, style, recipe, reason):
    project = Path(project).resolve()
    if not (project / 'project.json').is_file():
        raise ValueError('Project needs project.json; initialize the video project first')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', scene):
        raise ValueError('Scene must be a simple directory name')
    limits = {'swiss': ('S', 12), 'editorial': ('M', 16)}
    if style not in limits:
        raise ValueError('Style must be swiss or editorial')
    prefix, limit = limits[style]
    base_recipe = recipe[:-6] if recipe.endswith('-video') else recipe
    if base_recipe not in {f'{prefix}{n:02}' for n in range(1, limit + 1)}:
        raise ValueError('Recipe must belong to the selected upstream style')
    if not reason.strip():
        raise ValueError('Record why the recipe fits this scene')
    out = project / 'design' / scene
    if out.exists():
        raise ValueError('Design directory already exists; use a new version, do not overwrite')
    if not out.resolve().is_relative_to(project):
        raise ValueError('Design destination must stay inside the project')
    seed = DESIGN / f'assets/template-{style}-card.html'
    entry = DESIGN / 'SKILL.md'
    # Preserve the seed relative asset URLs and reject conflicting shared assets.
    source_assets = DESIGN / 'assets/screenshot-backgrounds'
    target_assets = project / 'design/assets/screenshot-backgrounds'
    copies = [(f, target_assets / f.relative_to(source_assets))
              for f in source_assets.rglob('*') if f.is_file()]
    for source, target in copies:
        if not target.resolve().is_relative_to(project):
            raise ValueError('Asset destination must stay inside the project')
        if target.exists() and (not target.is_file() or digest(source) != digest(target)):
            raise ValueError('Existing design asset differs; preserve it: ' + str(target))
    plan = {'status': 'draft', 'scene': scene, 'style': style, 'recipe': recipe,
            'reason': reason.strip(),
            'design_entry': 'design/guizang-social-card/SKILL.md',
            'entry_sha256': digest(entry),
            'seed': f'design/guizang-social-card/assets/{seed.name}',
            'seed_sha256': digest(seed),
            'note': 'Seed copied only. Read upstream recipe, fill content, localize fonts, render and inspect before review.'}
    out.mkdir(parents=True)
    shutil.copyfile(seed, out / 'index.html')
    for source, target in copies:
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    (out / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return out / 'index.html'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('--scene', required=True)
    parser.add_argument('--style', required=True, choices=['swiss', 'editorial'])
    parser.add_argument('--recipe', required=True)
    parser.add_argument('--reason', required=True)
    args = parser.parse_args()
    try:
        print(create_page(args.project, args.scene, args.style, args.recipe, args.reason))
    except ValueError as error:
        parser.exit(1, 'BLOCKED: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
