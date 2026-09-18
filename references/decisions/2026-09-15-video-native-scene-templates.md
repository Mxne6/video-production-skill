# Video-native scene templates

Date: 2026-09-15
Status: superseded in part by 2026-09-18 content-first scene composition

## Problem

The Skill described the Guizang social card system but did not provide executable video scene templates. `S01-S12` and `M01-M16` were documentation recipes, not different HTML files. `create_design_page.py` copied either the Swiss or Editorial social-card seed and recorded the recipe name, so video scenes could converge on one generic layout.

## Decision

Use six video-native structural templates for `1080x1440` XYZCHEM product videos:

- `opening`: opening promise or conclusion
- `product-hero`: product subject and defining attributes
- `mechanism`: mechanism, sequence, or relationship
- `proof-data`: evidence, comparison, or measurable proof
- `application`: operating context, application, or material detail
- `summary`: body conclusion before the fixed brand outro

Templates determine information structure. Social-card mode and palette determine visual tokens. A project fixes exactly one mode and one official palette: Swiss uses `ikb`, `lemon-yellow`, `lemon-green`, or `safety-orange`; Editorial uses `ink-classic`, `indigo-porcelain`, `forest-ink`, `kraft-paper`, `dune`, or `midnight-ink`. Images and factual content remain scene-specific. The shared `window.renderAt(t, duration)` contract, caption-safe area, deterministic seek behavior, and local-resource rules apply to every template.

The default templates use a sparse information budget because they are time-based video scenes, not paused social cards. Each scene keeps one headline, at most one supporting line, and two or three primary information units. Repeated footer labels and generic explanatory copy are omitted by default. The top rail remains as the single metadata anchor. This preserves the social-card visual language while avoiding competition with narration and subtitles.

The six structures are intentionally different so a video does not repeat the same left/right split on every scene:

- `opening`: full-canvas statement with one oversized index, based on the cover/statement recipes.
- `product-hero`: image-first composition with the product subject above and concise attributes below.
- `mechanism`: full-width vertical pipeline rather than three side-by-side cards.
- `proof-data`: stacked metric ledger rather than a KPI card grid.
- `application`: copy-first composition followed by a full-width image well.
- `summary`: pull-quote conclusion with a compact closing ledger.

These differences are structural, not palette variants. All six continue to inherit the same social-card typography, palette, grid, rules, and spacing tokens.

Images are treated as explanatory evidence rather than decoration. `product-hero` and `application` reserve large inspectable wells for product and real operating-context images. `mechanism` reserves a material, structure, section, or mechanism visual above its pipeline. `proof-data` reserves a test-result, chart, or evidence image above the metric ledger. `opening` and `summary` remain typographic unless a real image materially improves recognition or closure; they must not use generic decorative imagery just to satisfy an image quota.

`studio init --preset xyzchem` originally defaulted to `opening`. As of 2026-09-18, new projects default to the low-prescription `adaptive` seed and use the six structures below only as optional compatibility starters. Additional scenes still use `create_video_scene.py`. Generic `1920x1080` projects keep the existing `assets/scene.html` and `create_design_page.py` path in the first version.

Social card remains the tool for covers, single-page highlights, and reusable visual references. A normal video scene does not need to run the complete social-card recipe workflow. Video-native templates do not claim `section.poster` validation coverage; they bind a viewed PNG review directly.

## Rejected alternatives

- Creating 28 video templates from the social-card recipes: duplicates structure, increases maintenance, and does not solve selection semantics.
- Maintaining six layouts at both portrait and landscape dimensions: doubles the surface before the portrait workflow is proven.
- Replacing the video renderer or TTS engine: the renderer already consumes `scenes[].html`; the missing layer was templates.
- Auto-scaling portrait templates to landscape projects: produces unreliable composition and false compatibility claims.

## Compatibility

Existing projects are not migrated automatically. The fixed brand outro remains separate from `summary` and stays the last scene. Social-card snapshots and upstream references remain unchanged.

## 2026-09-18 amendment

The six-template approach fixed the lack of executable structure but over-coupled semantic intent to geometry. The accepted successor decision is `2026-09-18-content-first-scene-composition.md`: content is analyzed into a scene design brief before layout is chosen, `adaptive` is the default seed, and the six named templates remain supported without acting as routing rules.
