# TaxiMobile graphic asset library

This directory implements the production brief in [`docs/graphic_assets.txt`](../docs/graphic_assets.txt). It is the editable source-of-truth library; files copied into Compose resources are build-ready mirrors, not separate designs.

## What is ready

- Core logo, wordmark, splash, and adaptive-icon source layers
- One coherent landing/onboarding/permission/empty-state illustration family
- User, pickup, destination, saved-place, search, and selected map markers
- Standard and large/shared top-down taxi markers with documented center anchors and an upward zero-degree axis
- Matched standard and large/shared transparent service-card renders at 1024, 512, and 256 pixels
- Vector vehicle fallbacks for low-bandwidth or failed raster loading
- Route motifs, passenger/driver navigation icons, payment icons, safety icons, driver status motifs, document artwork, completion states, and earnings artwork

The machine-readable status and source/runtime mappings are in [`manifest.json`](manifest.json).

## Visual contract

- Brand colors: white `#FFFFFF`, navy `#0B1F3A`, secondary navy `#163A63`, mustard `#D6A800`, light mustard `#F3D76A`, and deep navy `#071426`.
- Illustrations remain white-dominant, use navy structure and restrained mustard emphasis, contain no localized text, and avoid named landmarks.
- Custom 24-pixel icons use a 1.75-pixel rounded stroke. Selected color is applied by UI tint.
- Vehicle-marker source artwork faces upward at zero degrees and rotates around its center (`0.5, 0.5`). Teardrop pins anchor at the bottom center (`0.5, 1.0`).
- Standard and large service renders face right and share the same shallow three-quarter camera and upper-left lighting direction.

## Runtime and fallbacks

Production assets are mirrored by basename to `TaxiMobile/shared/src/commonMain/composeResources/drawable`. The two generated service renders use their 512-pixel exports at runtime.

The app must remain usable if optional artwork cannot be decoded:

- landing artwork falls back to the existing Compose Canvas taxi scene;
- service cards fall back to `vehicle_silhouette_standard.svg` or `vehicle_silhouette_large.svg`;
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

## Deliberate exclusions

- Existing passenger and driver launcher icons are not overwritten by the editable A03 sources.
- Common authentication, profile, location, document, and action icons continue to use the app's Compose/Material icon family.
- Third-party payment marks, including CMI, stay deferred with their provider
  integrations. If one is approved later, only an official licensed asset may be
  added under `third-party/payment`; a handmade substitute is prohibited.
- Runtime 3D models, Lottie files, promotional graphics, and seasonal art stay deferred until a measured product need justifies their cost.
