# TaxiMobile graphic asset library

This directory implements the production brief in [`docs/graphic_assets.txt`](../docs/graphic_assets.txt). It is the editable source-of-truth library; files copied into Compose resources are build-ready mirrors, not separate designs.

## What is ready

- Core logo, wordmark, splash, and adaptive-icon source layers
- Thin light-navy taxi/Moroccan-architecture welcome portrait; earlier vector/stock candidates retained as legacy sources
- User, pickup, destination, saved-place, search, and selected map markers
- Standard and large/shared top-down taxi markers with documented center anchors and an upward zero-degree axis
- Matched standard and large/shared transparent service-card renders at 1024, 512, and 256 pixels
- Vector vehicle fallbacks for low-bandwidth or failed raster loading
- Route motifs, passenger/driver navigation icons, payment icons, safety icons, driver status motifs, document artwork, completion states, and earnings artwork

The machine-readable status and source/runtime mappings are in [`manifest.json`](manifest.json).

## Visual contract

- Brand colors: white `#FFFFFF`, navy `#0B1F3A`, secondary navy `#163A63`, mustard `#D6A800`, light mustard `#F3D76A`, and deep navy `#071426`.
- Most illustrations remain white-dominant with navy/mustard emphasis. The owner explicitly selected a navy-background welcome portrait with sparse light-navy taxi and Al-Qarawiyyin-inspired architectural contours. It contains no localized text, provider mark or claim of institutional endorsement.
- Custom 24-pixel icons use a 1.75-pixel rounded stroke. Selected color is applied by UI tint.
- Vehicle-marker source artwork faces upward at zero degrees and rotates around its center (`0.5, 0.5`). Teardrop pins anchor at the bottom center (`0.5, 1.0`).
- Standard and large service renders face right and share the same shallow three-quarter camera and upper-left lighting direction.

## Runtime and fallbacks

Production assets are mirrored by basename to `TaxiMobile/shared/src/commonMain/composeResources/drawable`. The two generated service renders use their 512-pixel exports at runtime.

The owner subsequently rejected the code-authored vector attempt and explicitly
requested image generation for fine light-navy outline art on navy, then a taller
phone composition with fewer lines. The selected 941x1672 (approximately 9:16) PNG is recorded in
[`illustrations/onboarding/prompts.md`](illustrations/onboarding/prompts.md), with
provenance in [`illustrations/onboarding/LICENSE.md`](illustrations/onboarding/LICENSE.md).
It is copied unchanged to runtime, not cropped, recoloured or resized. The
shared welcome displays the complete portrait at up to 216x384 dp and shrinks
proportionally on narrower screens. RGB without alpha is intentional for this
solid-background asset only; cutout assets still require alpha. Its byte limit
is explicitly 2 MiB; other optional assets retain the 1 MiB limit.
The earlier 4:5 PNG, unDraw and code-authored SVGs remain legacy candidates, not active artwork.
The brand mark
and vehicle silhouette also have exact PNG runtime exports. Shared Android UI
must not load SVG through `painterResource`: Android does not support that format.
The optional-artwork loader checks PNG signature/size, contains read/decode
failures, and preserves cancellation. Operational resources remain fail-closed.

The app must remain usable if optional artwork cannot be decoded:

- landing artwork falls back to a simple light-navy outlined Canvas taxi scene on navy, with the same portrait bounds and accessibility description;
- the vehicle placeholder uses the standard silhouette's PNG export, then
  falls back to a localized-label-derived geometric/text placeholder;
- MapLibre markers retain programmatic circle/halo geometry until image registration succeeds;
- selected/offline/searching states remain programmatic so animation, bearing, opacity, and accessibility state cannot drift from app state;
- manual bank/M-Wallet transfer uses a first-party generic icon or localized
  label; no third-party provider mark is needed, and cash remains supported;
- the country selector uses ISO code plus dialing code and does not require flags.

## Exporting

Vehicle-render masters and accepted prompts live under `vehicles/renders/source` and [`vehicles/renders/prompts.md`](vehicles/renders/prompts.md). Rebuild normalized PNGs with:

```powershell
python assets/tools/export_vehicle_renders.py
```

This requires Pillow only at design time. Rebuild required PNG handoff exports from the square logo and vehicle-marker SVGs with:

```powershell
npm install --no-save playwright
npx playwright install chromium
node assets/tools/export_svg_rasters.cjs
```

On a machine with an existing Chromium-compatible browser, `TAXI_ASSET_BROWSER_PATH` can point at its executable. Neither tool is an app runtime dependency.

Rebuild the selected welcome, brand-mark and vehicle-silhouette PNGs together:

```powershell
node assets/tools/export_svg_rasters.cjs --runtime-only
```

This uses the existing design-time Playwright/browser setup. It copies the
selected portrait unchanged and preserves the other SVGs' viewBox/transparency.
It does not rewrite unrelated handoff/catalog images. Do not substitute earlier
stock, generated 3D or code-authored outline candidates. Existing generated
service-render material does not change the selected welcome direction.

## Deliberate exclusions

- Existing passenger and driver launcher icons are not overwritten by the editable A03 sources.
- Common authentication, profile, location, document, and action icons continue to use the app's Compose/Material icon family.
- Third-party payment marks, including CMI, stay deferred with their provider
  integrations. If one is approved later, only an official licensed asset may be
  added under `third-party/payment`; a handmade substitute is prohibited.
- Runtime 3D models, Lottie files, promotional graphics, and seasonal art stay deferred until a measured product need justifies their cost.
