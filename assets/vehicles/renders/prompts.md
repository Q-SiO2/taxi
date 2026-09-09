# Vehicle render generation record

The two accepted masters were created with the built-in image-generation tool in transparent-output mode. The tool did not expose a model-version identifier, so none is claimed here. These prompts are kept with the sources so a later service variant can match the same visual family.

## Standard city taxi

```text
Create a polished, simplified high-quality 3D product render of one unbranded compact four-door city taxi. Show a shallow three-quarter front-side view with the vehicle facing right. Lock the camera at a modest height with a natural medium focal length. Use a mustard-yellow body with restrained deep-navy lower trim and mirror accents, a small taxi roof light, neutral realistic windows and wheels, and no manufacturer badge, writing, license number, flag, or scenery. Light it with a large soft key from the upper left and a mild fill from the opposite side. Keep reflections controlled and include only a very subtle contact shadow. Isolate the complete vehicle on a genuinely transparent alpha background with generous even padding. Center it on a square canvas. No border, gradient, floor, backdrop, text, watermark, or logo.
```

Accepted source: `source/vehicle_render_standard_generated_master.png`

## Large/shared taxi

```text
Create a polished, simplified high-quality 3D product render of one unbranded long-body MPV used as a large or shared taxi. Match this production family exactly: shallow three-quarter front-side view, vehicle facing right, modest camera height, natural medium focal length, soft key light from the upper left, mild opposite fill, controlled reflections, and a subtle contact shadow. Make the vehicle clearly longer, taller, and more spacious than a compact sedan. Use a predominantly white body, deep-navy roof and lower trim, one restrained mustard side stripe, and a small mustard taxi roof light. Include neutral realistic windows and wheels. Do not include manufacturer badges, writing, license numbers, flags, people, luggage, scenery, or road. Isolate the complete vehicle on a genuinely transparent alpha background with generous even padding and center it on a square canvas. No border, gradient, floor, backdrop, text, watermark, or logo.
```

Accepted source: `source/vehicle_render_large_generated_master.png`

## Rejection criteria

Generated candidates are rejected if transparency is simulated with a checkerboard, if a broad background glow remains, if any vehicle edge is clipped, or if the angle and lighting no longer match the accepted pair.
