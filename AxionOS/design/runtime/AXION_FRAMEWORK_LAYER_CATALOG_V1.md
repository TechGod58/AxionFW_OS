# AXION Framework Layer Catalog v1

Purpose: catalog immutable prebuilt framework layers used for fast capsule cloning.

## 1) Layer Types

- `office-lite` (docs/spreadsheets/presentations baseline)
- `dev-core` (build/runtime essentials)
- `media-core` (render/transcode/playback stack)
- `ai-infer` (model runtime + acceleration libs)
- `web-app` (browser/webview execution baseline)

## 2) Catalog Entry Format

```json
{
  "layer_id": "office-lite",
  "version": "1.0.0",
  "base_os_abi": "axion-abi-v1",
  "arch": "x86_64",
  "digest": "<sha256>",
  "size_mb": 420,
  "capabilities": ["clipboard", "printing", "fonts"],
  "gpu_support": ["none", "shared"],
  "warm_cache_priority": 80
}
```

## 3) Rules

- Layers are immutable once published.
- New behavior => new version.
- Capsule blueprints pin exact layer version.
- Integrity digest mandatory for load.

## 4) Warm Cache Strategy

- Keep top-N layers hot based on usage + startup SLA pressure.
- Evict least-recent low-priority layers first.
- Persist cache metrics for startup tuning.

## 5) Board-Agnostic Behavior

- Catalog advertises capability requirements.
- Resolver matches layer to host capabilities.
- If capability gap: choose compatible fallback layer or DENY deterministically.

## 6) v1 Acceptance

- At least 2 layer types available with versioned entries.
- Layer integrity validated before clone.
- Warm cache hit/miss stats visible in telemetry.
