# AXION Threat Screening Pipeline v1

Purpose: security scanning at ingress, transit, and promotion points with privacy-first operation.

## 1) Principles

- Security should be effective without spyware behavior.
- Local-first scanning by default.
- No silent telemetry exfiltration.
- Deterministic allow/deny/quarantine decisions.

## 2) Scan Stages ("before port" to OS placement)

1. **Pre-Port Gate (Edge Broker)**
   - Network/USB ingress broker inspects metadata and policy before payload reaches userland services.
   - Applies protocol/type allowlists and known-bad signatures.

2. **Port Ingress Scan**
   - Deep scan on ingress stream/file object.
   - Risk score + type validation + decompression guards.

3. **Staging Scan**
   - Objects moved to untrusted staging zone.
   - Multi-engine local scan + heuristic checks.

4. **Promotion Scan**
   - Existing promotion pipeline checks hash/signature/policy/IG.
   - Final verdict before trusted storage placement.

5. **Runtime Watch (Post-placement probation)**
   - Short watch window for suspicious behavior; auto-quarantine on trigger.

## 3) Coverage Targets

- Downloads (browser, package imports)
- USB device payloads and mount content
- Email/message attachment imports
- Remote session file transfers (RDP/VNC/SSH channels)
- Driver package staging

## 4) Privacy Guardrails

- No full-file cloud upload by default.
- Optional reputation lookups only on hash/signature, user-opt-in.
- Local logs remain local unless exported by user/admin.
- Explicit toggle for telemetry with clear labels.

## 5) Decision Codes

- `THREAT_OK`
- `THREAT_QUEUE_ANALYSIS`
- `THREAT_REJECT_SIGNATURE`
- `THREAT_REJECT_POLICY`
- `THREAT_REJECT_MALWARE`
- `THREAT_QUARANTINE`

## 6) User Experience

- Fast default path for clean content.
- Clear reason code for blocked items.
- One-click quarantine review for admins.
- No spammy popups; consolidated notifications.

## 7) Definition of Done (v1)

- Every inbound payload class passes at least two security gates before trusted storage.
- Quarantine path and restore policy are auditable.
- Privacy settings are explicit and default to local-first.
