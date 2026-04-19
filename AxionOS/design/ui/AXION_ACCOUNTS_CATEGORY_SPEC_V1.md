# AXION Accounts Category Spec v1

Purpose: close out Accounts category with local-first identity controls.

## Sections
- Profile (display name, handle, avatar)
- Sign-in options (password/PIN/biometric toggle placeholders)
- Security options (MFA status, recovery options)
- Session controls (lock/sign out/switch user)
- Account type (Operator/Admin/Service visibility)

## Actions
- Update display name/handle
- Toggle sign-in methods (policy-aware)
- Regenerate recovery codes (stub)
- Session lock/sign-out request

## Done criteria
- Runtime host exists and persists account state
- Emits corr-traced account events
- Integrates with existing identity UX principles
