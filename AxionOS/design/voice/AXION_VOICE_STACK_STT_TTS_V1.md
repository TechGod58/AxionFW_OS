# AXION Voice Stack Spec v1 (STT + TTS)

Purpose: deliver high-quality speech-to-text and text-to-speech as first-class OS services.

## 1) Goals

- Excellent recognition in real-world noisy rooms
- Strong speaker focus (user voice priority)
- Low-latency dictation/command mode
- Natural TTS for system + app usage
- Local-first option to protect privacy

## 2) STT Modes

1. Dictation mode
- punctuation assist
- continuous transcription
- custom vocabulary injection

2. Command mode
- strict grammar + wake phrase optional
- low false-trigger profile

3. Meeting/transcript mode
- multi-speaker diarization (phase 2)
- timestamped segments

## 3) STT quality pipeline

- beamforming / mic array support where available
- noise suppression + echo cancellation
- voice activity detection
- speaker adaptation profile
- confidence scoring per segment

## 4) "Hears everything except me" fix strategy

- Per-user voice profile enrollment
- priority speaker lock (voiceprint-assisted, optional)
- adaptive gain and noise floor tuning wizard
- mic input diagnostics + placement guidance
- fallback to push-to-talk mode when environment is chaotic

## 5) TTS Modes

- System narration voice
- Notification voice
- Long-form reading/story mode
- App API voice synthesis

Features:
- voice selection (warm/neutral/pro)
- speed/pitch/tone controls
- expressive mode toggle
- offline voice pack support

## 6) Runtime architecture

- `voice-broker` host service (policy + routing)
- STT/TTS engines run as isolated workers (capsule-compatible)
- app access via permissioned Voice API

## 7) Privacy & security

- local-first processing default
- cloud model optional and explicit
- no raw audio exfil by default
- redact-sensitive transcript mode
- per-app microphone permission controls

## 8) Performance targets (v1)

- command recognition latency: <300ms target (local)
- dictation streaming latency: <700ms target
- TTS start latency: <250ms warm

## 9) Quality targets

- high recognition accuracy in normal room noise
- robust punctuation in dictation mode
- clear natural TTS with minimal artifacts

## 10) Definition of done

- STT and TTS are available system-wide
- User can run calibration to improve recognition
- Voice stack works with accessibility tools and shell commands
