# Thin-line Moroccan welcome portrait — generation record

The owner explicitly requested image generation after rejecting the vector
attempt, preferred the generated navy/light-navy direction, then requested a
phone-oriented aspect ratio and less dense linework. This record supersedes the
earlier non-AI preference for this asset. Final owner approval is still required.

Tool: built-in image generation, opaque output. No model identifier was exposed.
The selected native output is 941x1672, approximately 9:16, 8-bit RGB PNG.
Master: `source/illustration_landing_navy_outline_master.png`.
Runtime: `exports/illustration_landing_runtime.png`, copied byte-for-byte into
Compose resources. Re-export with `node assets/tools/export_svg_rasters.cjs --runtime-only`.
No crop, resize, recolour or artistic processing is part of export.

## Generation sequence

1. New landscape image: refined thin light-navy architectural contour linework
   on deep navy, one believable unbranded compact taxi, Al-Qarawiyyin-inspired
   square minaret and pitched-roof pavilion/arcade; no UI, written copy or logos.
2. Targeted edit: remove the manufacturer-like grille badge and the extra tiny
   upper minaret tower. Preserve the vehicle, colours, line style and viewpoint.
3. Earlier edit: recompose to 4:5 portrait and remove excessive detail, below.
4. Latest selected edit (2026-10-04): recompose to 9:16 and further simplify
   wheels, headlight machinery, car interior and repeated architectural contours.

Architectural references were viewed, not submitted as model inputs. The legacy
unDraw illustration was never submitted to generation. See `LICENSE.md`.

## Earlier 4:5 edit prompt (retained legacy)

```text
Edit the immediately preceding refined thin light-navy line illustration of a taxi and Fez/Al-Qarawiyyin-inspired architecture on deep navy. The owner likes this direction; PRESERVE the delicate thin light-navy colour, dark navy background, believable taxi proportions and architectural identity. Change only the requested mobile composition and excessive detail.
1. OUTPUT A PORTRAIT 4:5 COMPOSITION for a phone welcome illustration, approximately 1024 x 1280 rather than the current wide landscape. RECOMPOSE the scene, do not simply crop, stretch or distort. Keep the whole compact taxi visible in the lower foreground, both main wheels and its small unlettered roof light intact, and the full square minaret and finial safely inside the top. Use one pitched-roof courtyard pavilion and a small horseshoe arcade behind the taxi. Cohesive architectural composition with balanced negative space, not scattered icons. All important subjects must remain clear at roughly 256 x 320 mobile display pixels.
2. SIGNIFICANTLY REDUCE LINE DENSITY, by at least two-thirds. This is elegant sparse editorial contour drawing, NOT an etching packed with micro-detail. Remove the tree/foliage entirely. Remove wall hatching, tiny zellij/stucco patterns, masonry textures, individual roof-tile scallops, crowded floor lines, repeated wooden corbel details and internal seat/upholstery lines. Simplify wheels to clean outer/inner circles and only a few clean spokes, roof to its main silhouette and a few structural ridge lines, grille to a few horizontal lines, arches to simple graceful horseshoe outlines. Keep the taxi silhouette, windows, mirrors, headlights, roof light and architectural structural contours, but no small repeated ornamental patterns. Use large quiet navy areas between beautifully composed fine strokes.
Architecture still includes the plain square minaret with paired narrow upper arched windows, a restrained crenellated crown and slender finial, and the characteristic hipped-roof pavilion / horseshoe arches. No added little lantern tower above the minaret, no onion domes or fantasy buildings.
Constraints: remain a sophisticated very thin LIGHT NAVY (#8AA6C5-like) outline on deep NAVY (#0B1F3A-like). NO white outlines, yellow, gold, bright/neon blue, glows, thick comic strokes, shading, gradients, grain or fill-coloured subjects. No text, car manufacturer badge, plate characters, people, tree, logos, watermarks, decorative borders, maps, checkmarks, stars, moon or UI components.
```

## Exact latest selected edit prompt

```text
Use case: style-transfer. Edit target: the attached existing navy thin-line taxi and Al-Qarawiyyin-inspired architecture illustration. Owner likes this visual direction; change ONLY its portrait framing and excess line density. Output a tall smartphone 9:16 portrait, ideally 1152x2048. RECOMPOSE, do not stretch or crop. Keep the entire unbranded believable compact Moroccan taxi in lower foreground, both visible wheels and tiny unlettered roof light; keep full square minaret and slender finial behind, and one recognizably Moroccan pitched-roof pavilion with just THREE simple horseshoe arches. Center the coherent scene with generous navy margins, safe from clipping. Remove about half of the remaining contours: use SINGLE fine contours instead of doubled outlines; remove all interior seats/steering wheel, road/paving grid, repeating arcade beyond pavilion, column mouldings, trim repetitions, tire tread, wheel spoke clusters, detailed headlight machinery, multiple bumper/grille lines. Wheels two clean circles with at most three spokes; headlights one simple shape each; roof main silhouette and two ridge lines only. Preserve fine elegant LIGHT NAVY (#8AA6C5-like, subdued not white) outlines on a flat deep NAVY (#0B1F3A-like) background, recognizable taxi silhouette and square Moroccan minaret with paired arched windows. Plenty of quiet negative space. No text, manufacturer badge, plate letters, people, trees, gradients, glow, textures, hatching, shading, yellow/gold, white strokes, borders or UI. This is minimalist premium editorial contour illustration, not an architectural technical drawing. Make line work clean and readable at small phone display sizes.
```

The tool returned 941x1672 rather than the suggested dimensions; the original
pixels are retained. The complete taxi and finial fit, three pavilion arches
remain, and paving, seats and intricate wheel/headlight detail were removed.
Some paired contours remain. The actual image, not requested line percentages,
is the delivered result. Its 1,193,100 bytes remain within the existing 2 MiB
optional-image budget; no loader limit was raised.

## Inspection and boundaries

The selected revision has the complete car and minaret in frame, removed foliage
and dense wall/roof patterning, an unbranded grille, and no written copy. Some
automotive/window contours remain; the actual image, not the prompt's requested
percentage, determines the delivered visual. This is a stylised architectural
scene, not an exact survey or a claim about vehicle access to the courtyard.
Inspect at phone display size before visual acceptance. Image RGB shades do not
change application theme tokens or represent map/ride/payment authority.
