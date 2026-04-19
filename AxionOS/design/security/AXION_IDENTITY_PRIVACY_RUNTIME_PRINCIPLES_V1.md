# AXION Identity, Privacy & Runtime Principles v1

## Captured directives

1) No forced online account creation
- Local account setup must be supported by default.
- Cloud/SSO link is optional and can be done later.

2) Biometrics are optional convenience
- Password/passphrase (or key) remains primary trust anchor.
- Biometrics are not sole recovery path.

3) MFA/2FA support
- TOTP/security key/backup codes supported.
- Required for admin-sensitive actions (policy/elevation/remote access) by policy.

4) Privacy-first logging
- Log errors/changes/security decisions only by default.
- No snooping-style content logging defaults.
- Disk Cleanup includes non-required log purge path.

5) Startup/background control
- No silent auto-start/background persistence for newly installed apps.
- User right-click controls startup enable/disable.

6) Capsule runtime invariant
- App closed => capsule/VM terminated.
- No hidden background runtime unless explicitly approved service policy.

7) Sandboxed install/update model
- All installs/updates are tested in VM/capsule first.
- Promote to OS only after scan/policy/IG pass.

## Status
These principles are now part of AxionOS design baseline and should be treated as product defaults unless explicitly overridden by policy.
