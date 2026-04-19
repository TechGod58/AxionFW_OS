# AXION Creative Studio Spec v1

Product concept: cross between Paint and Photoshop with modular effect packs.

## Name
- Product: **Axion Creative Studio**
- ID: `axion-creative-studio`

## Positioning
- Fast/simple like Paint for quick edits
- Layer/effects workflow like Photoshop (lighter scope)
- Local-first creative tool integrated with Axion sandbox/promotion model

## Core v1 features

1. Canvas + tools
- Brush, eraser, fill, shape, text
- Selection tools (rect/free)
- Crop/resize/rotate

2. Layers (essential)
- add/delete/reorder
- opacity/blend basic modes

3. Adjustments
- brightness/contrast/saturation
- temperature/tint
- sharpen/blur

4. Effects pipeline
- non-destructive effect stack per layer
- preview on/off toggle

5. Export
- PNG/JPG/WebP
- project format with layer retention (`.axproj`)

## Camera integration
- open image/video frame captures directly from Axion Camera
- one-click "Edit in Creative Studio"

## Security/runtime
- app runs as capsule workload by default
- imports/exports pass promotion policy for persistent writes

## v1 non-goals
- full Photoshop feature parity
- advanced RAW workflow
- AI generation stack
