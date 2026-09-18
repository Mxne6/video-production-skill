# Content-first scene composition

Date: 2026-09-18
Status: accepted

## Context

The 2026-09-15 change introduced six executable portrait video templates to stop every scene from collapsing into one generic social-card seed. That solved missing implementation structure, but it also created a new failure mode: semantic scene labels became geometry selectors. Agents could choose `proof-data`, `mechanism`, or `application` before understanding the actual visual argument, then replace placeholders inside a fixed silhouette.

This produced technically valid scenes that were individually clean but mechanically similar across a video. Images often occupied predefined wells rather than determining the composition. The documentation already said “templates are starters,” but the executable API still made template choice the first concrete design action.

The Guizang social-card system's transferable advantage is not its recipe count. Its stronger ideas are content compression, one focal point, image-as-evidence, typographic hierarchy, subject-aware cropping, explicit information budgets, and review of the final rendered image. Those principles need a video-native decision layer before HTML geometry.

## Decision

Introduce a content-first scene design contract for new `1080x1440` XYZCHEM projects.

1. New projects set `design_contract_version: 1`.
2. Each body scene contains `scenes[].design`, including message, viewer task, dominant element, attention order, on-screen vs narration-only split, image role/share, layout family/signature, density/intensity, composition reason, whitespace reason, and continuity reason.
3. `studio init --preset xyzchem` and `create_video_scene.py` default to a new low-prescription `adaptive` seed.
4. The six existing templates remain supported as optional compatibility starters; they are no longer semantic routing rules.
5. Static design review validates the design brief and refuses untouched adaptive starter markup.
6. Production gating validates the design contract and basic whole-video rhythm.
7. The visual content identity includes the design brief only for projects that opt into the new contract, preserving legacy project compatibility.

## Composition model

Use a small grammar rather than a growing template catalog:

- `type-led`
- `image-led`
- `data-led`
- `relation-led`
- `mixed`

These are not templates. The actual `layout_signature` describes the silhouette produced for the content.

The dominant element must materially own the frame. A hero image should normally own at least 55% of useful visual area; a primary number should not be trapped in a small KPI card; a relationship should produce spatial structure; a statement may legitimately use sparse composition without decorative filler.

## Sequence model

The video is reviewed as a sequence as well as scene-by-scene.

Three consecutive scenes with the same `layout_signature` fail by default unless repetition has an explicit continuity/comparison reason. Same-family streaks and flat intensity receive warnings. These checks are intentionally conservative and do not replace contact-sheet review.

The goal is not forced variety. It is “unified but not repeated”: shared tokens and visual language, different geometry when content demands it.

## Compatibility

Existing projects without `design_contract_version` continue to use their recorded scene files and reviews. They are not migrated automatically.

The fixed brand outro is excluded from the scene design contract. Generic `1920x1080` projects retain the existing legacy scene path.

## Supersedes

This decision partially supersedes the semantic routing portion of `2026-09-15-video-native-scene-templates.md`. The six named templates themselves remain supported.
