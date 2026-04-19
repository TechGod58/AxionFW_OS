# AXION Video Studio Spec v1

## Product
- Name: **Axion Video Studio**
- ID: `axion-video-studio`

## Goal
Provide core video editing and conversion tools natively to reduce third-party dependency and improve security posture.

## Core v1 features

1) Timeline editing (basic)
- trim/cut
- split clips
- join/merge clips
- reorder timeline
- simple transitions (fade/cut)

2) Effects (requested)
- brightness/contrast/saturation
- color filters/LUT-lite
- sharpen/blur
- vignette/grain (basic)
- text/title overlays

3) Format + version conversion
- container conversion: mp4, mkv, mov, webm
- codec profile presets: H.264/H.265/VP9/AV1 (where supported)
- quality presets: low/medium/high/source-like
- frame rate conversion presets
- resolution scaling presets

4) Utilities
- Video splitter (by time markers)
- Video joiner (same/compatible profiles with transcode fallback)
- Batch conversion queue

## Safety/runtime
- Runs as capsule workload by default
- Import/export paths go through promotion/security policy
- No unsigned third-party codec bundles loaded by default

## UX
- drag/drop media bin
- side-by-side preview
- export wizard with device presets
- job queue with progress/errors

## v1 non-goals
- full pro NLE feature parity
- advanced motion tracking/VFX
- cloud render dependency

## v1 definition of done
- user can split, join, apply basic effects, and export to multiple formats reliably
- conversions are policy-audited and recoverable on failure
