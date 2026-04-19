# AXION Effects Module Marketplace v1

Goal: low-cost add-on effects system with safe module loading and post-purchase upsell.

## Business model
- Core app includes solid base effects.
- Optional add-on packs at phone-app pricing.
- Keep packs cheap to maximize adoption.

### Pricing bands (proposal)
- Basic pack: $0.99 - $2.99
- Pro pack: $3.99 - $7.99
- Creator bundle: $9.99 - $14.99

## Module types
- Color grading packs
- Film/grain packs
- Portrait/skin packs
- Stylization packs (comic, neon, cyber, etc.)
- Video LUT/effect packs (phase 2)

## Module format (concept)
- signed package with metadata + effect kernels + previews
- installed to sandboxed module directory
- loaded only after signature and policy validation

## Safety rules
- no unsigned modules
- no arbitrary native code execution in effect modules (v1)
- effect modules run in constrained plugin sandbox
- module updates follow sandbox test -> promote path

## Upsell strategy (not predatory)
- contextual recommendations based on used tools
- transparent pricing and one-tap trial
- no dark patterns, no forced subscriptions

## User trust controls
- clear "what this pack adds"
- disable/remove modules anytime
- local receipt cache and reinstall entitlement

## Metrics (privacy-first)
- local-first usage analytics
- optional opt-in telemetry for aggregate effect popularity

## v1 definition of done
- install/uninstall effect module works safely
- purchased module unlock reflected instantly
- effects apply non-destructively with preview
