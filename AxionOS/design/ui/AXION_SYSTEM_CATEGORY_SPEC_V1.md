# AXION System Category Spec v1

Purpose: provide core system controls/status in one category pass (closeout sprint).

## Sections
- About (version/build/channel)
- Performance snapshot (cpu/mem/storage/gpu)
- Storage controls (cleanup + usage)
- Recovery shortcuts (checkpoint/restore)
- Display/graphics quick controls (quality/effects)

## Actions
- Open cleanup
- Open checkpoint manager
- Set graphics quality profile
- Toggle visual effects/transparency policy

## Done criteria
- Runtime host exists and returns state payload
- Emits corr-traced system events
- Integrates with settings + desktop graphics policy
