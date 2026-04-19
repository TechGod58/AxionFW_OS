# MILESTONE_AUDIO_SYSTEM_V1

## Goal
Provide optional keystroke milestone feedback (sound/voice) as a positive, user-controlled feature.

## Scope (v1)
- Track cumulative keystrokes.
- Trigger milestone events at configurable thresholds.
- Play built-in or custom sounds/voice lines.
- Keep behavior safe, short, and non-disruptive.

## Principles
- Opt-in only.
- Easy mute/disable.
- No deceptive messaging.
- Max playback duration enforced.

## Default Milestones
- 100000
- 500000
- 1000000

## Settings Contract (JSON)
```json
{
  "milestones_enabled": true,
  "milestones": [100000, 500000, 1000000],
  "output_mode": "sound",
  "builtin_pack": "subtle",
  "custom_sounds_dir": "<AXIONOS_ROOT>/assets/sounds/custom",
  "custom_map": {
    "500000": "500k.wav",
    "1000000": "1m.wav"
  },
  "max_play_sec": 2.0,
  "mute_hotkey": "Esc",
  "cooldown_sec": 10,
  "track_scope": "active_session"
}
```

## Built-in Packs
- subtle: short neutral confirmation tones.
- fun: playful short voice/sfx.
- chaos: optional novelty set (disabled by default).

## Event Contract
Emit on trigger:
- `MILESTONE_HIT`
  - `milestone`
  - `keystroke_count`
  - `correlation_id`
  - `pack`
  - `asset`

## Safety/UX Guardrails
- Playback max 2.0s.
- Do not stack overlapping audio.
- If asset missing -> fallback to built-in subtle tone.
- Global quick mute always available.

## Audit
Write append-only line to audit log:
- timestamp_utc
- milestone
- selected_asset
- source (builtin/custom)
- correlation_id

## Future Extensions
- Weekly/monthly streak badges.
- Per-app milestone scopes.
- User-recorded voice pack manager.

