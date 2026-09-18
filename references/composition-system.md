# Content-first scene composition system

This is the visual decision layer for portrait video scenes. It translates Guizang's design method into a time-based medium without turning social-card recipes into video templates.

## The principle

Do not choose a layout from the scene label. A scene is designed only after its communication job is clear.

Before touching HTML, answer six questions:

1. What is the one thing the viewer should understand first?
2. What is the strongest evidence for that idea: image, product, number, relationship, quote, or process?
3. What belongs on screen, and what should stay in narration?
4. How many attention stops fit the scene duration?
5. How much of the canvas should the dominant element own?
6. What visual energy should this scene contribute between the previous and next scenes?

The scene type (`opening`, `proof-data`, etc.) may describe editorial intent, but it must not determine geometry.

## Required scene design brief

Every new XYZCHEM scene carries a `design` object in `project.json`. Complete it before static design review.

```json
{
  "status": "ready",
  "message": "What the viewer should understand in one sentence",
  "viewer_task": "verify",
  "dominant": "evidence",
  "layout_family": "image-led",
  "layout_signature": "large-evidence-top / compact-result-bottom",
  "attention_order": ["test image", "primary result", "source condition"],
  "on_screen": ["28 d", "+31%", "test condition"],
  "narration_only": ["method detail", "secondary caveat"],
  "image_role": "evidence",
  "visual_share": 0.62,
  "density": "balanced",
  "intensity": "strong",
  "contrast_with_previous": "increase",
  "composition_reason": "The test image is the proof; numbers annotate it rather than compete with it.",
  "whitespace_reason": "Quiet right edge keeps the result readable over subtitles.",
  "continuity_reason": ""
}
```

`layout_signature` is intentionally free-form. It describes the actual silhouette, not a template ID. Examples: `full-bleed-photo / lower-left-title`, `type-left / product-right-vertical`, `number-center / source-bottom`, `relation-diagonal / labels-edge`.

## Five composition families, not five templates

These are starting grammars only. Build the geometry from the content.

- **type-led** — one statement, short conclusion, contrast phrase, or identity moment. Typography is the subject. Do not add a small image merely to fill space.
- **image-led** — product, photo, test result, material detail, screenshot, or atmosphere is the evidence. The image should normally own 55-85% of the useful canvas when it is the hero.
- **data-led** — one number or comparison is the first read. Let the number become a spatial event; supporting labels and source conditions are secondary.
- **relation-led** — mechanism, sequence, cause/effect, before/after, or system relation determines the geometry. Connections must be visible, not described by a row of unrelated cards.
- **mixed** — use only when two media truly share the argument. Mixed does not mean "put text on the left and an image on the right" by default.

Within a family, compose with primitives: full bleed, asymmetric split, narrow marginal column, vertical ledger, long image strip, anchored number, diagonal relation, stacked evidence, or a quiet statement field. These are moves, not recipes.

## Dominance law

Every scene needs one dominant element. Everything else supports it.

- If the **image is the point**, make it large enough to inspect. Text should attach to the image, frame it, or occupy its quiet zone.
- If a **number is the point**, the number should be the first viewport signal. Do not bury it inside a metric card grid.
- If a **sentence is the point**, let type and whitespace carry the frame. Do not manufacture metadata or decorative widgets.
- If a **relationship is the point**, the relationship itself becomes the composition: distance, direction, grouping, sequence, overlap, or contrast.
- If the **product is the point**, its silhouette and orientation should determine the text axis and negative space.

A useful test: blur the frame mentally. The largest visual mass should still correspond to the most important information.

## Image integration

An image is not "a slot". Its role changes the whole scene.

- `hero`: composition begins with the image. Reserve 55-85% visual share.
- `evidence`: the image must be inspectable and physically close to the claim it supports.
- `support`: smaller image is allowed, but it should resolve a concrete question, not decorate.
- `atmosphere`: use sparingly for opening/transition/closure; narration carries most facts.
- `none`: do not add an image quota.

Decide crop and safe zones before generating or selecting the asset. If a supplied image cannot survive the intended crop, change the composition instead of forcing `cover`.

## On-screen information budget

Video is not a paused poster. The visible layer should usually have 1-3 attention stops.

- <= 4 seconds: normally 1-2 stops.
- 4-7 seconds: normally 2-3 stops.
- 7+ seconds: 3 stops is still the default; reveal states can sequence details.

Put explanation, qualifiers, and connective language in narration unless the viewer must inspect them visually. Do not duplicate the narration as body copy.

## Whitespace

Whitespace is an assigned region, not leftover area. Record its job in `whitespace_reason` when it materially shapes the scene: protect a face, isolate a number, give a product silhouette air, reserve subtitle clearance, or create a quiet beat after a dense scene.

Do not center a thin block in the canvas and call the remaining area editorial whitespace. If empty space has no role, redesign the composition.

## Guizang identity without social-card mimicry

Keep the shared visual language:

- large, restrained typography; larger display means lighter visual weight;
- asymmetric alignment and deliberate negative space;
- straight edges, hairline rules, columns and ledgers before rounded containers;
- one palette and one typographic system across the video;
- images as evidence or atmosphere, not decorative thumbnails;
- strong contrast between focal and supporting information.

Do not import social-card-only behavior:

- no page-density quota just because cards need to fill a swipe canvas;
- no obligatory issue strips, page numbers, kicker rows, or recipe metadata;
- no `Mxx` / `Sxx` labels as a scene layout decision;
- no static-card body paragraphs that compete with narration;
- no repeated card matrices merely because they validate well.

## Sequence rhythm: unified, not repeated

Judge the video as a strip of scenes, not as isolated PNGs.

Track for each scene: `layout_signature`, dominant element, density, intensity, and image role.

- Repeating the same silhouette three scenes in a row is a design failure unless the repetition itself communicates continuity; write `continuity_reason` when intentional.
- Two image-led scenes may be adjacent when the content demands it, but they should not automatically use the same image proportion and title position.
- A dense mechanism/evidence scene often benefits from a quieter type-led or image-led beat after it.
- Strong → strong → strong is acceptable only when the story is genuinely escalating. Otherwise vary energy through scale, density, or media.
- Do not alternate layouts mechanically. Rhythm follows the argument: setup, reveal, proof, explanation, consequence, closure.

Review the contact sheet at thumbnail size. If every frame has the same large rectangle, same title band, or same vertical split, the system is still template-driven even if each frame is individually clean.

## Design loop

1. Complete the scene design brief.
2. Choose or author a composition hypothesis.
3. Build from the `adaptive` seed or deliberately repurpose a named starter.
4. Render a static PNG.
5. Inspect at full size and thumbnail size.
6. Compare with adjacent scenes in the `visual_review.py` midpoint contact sheet.
7. If the dominant element, attention order, or sequence rhythm is wrong, change geometry before polishing color or motion.
8. Only after static composition passes should motion/reveal timing be attached.

Motion is the final layer. It cannot rescue a weak composition.
