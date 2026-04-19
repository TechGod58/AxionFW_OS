# QA

All subsystem integration and release gating follows `CONTRACT_FIRST_DEVELOPMENT_LOOP_V1`.

Primary smoke runners:
- `run_phase2_shell_smoke.py`: Shell host/router functional smoke.
- `run_master_smoke.py`: Cross-subsystem smoke for launcher/device fabric.
- `run_security_core_smoke.py`: Security-critical pass/fail contract smoke (identity, secrets, entropy).
- `run_kernel_policy_contract_smoke.py`: Kernel policy contract smoke (syscall-only scheduler policy writes + security precedence selftest wiring).
- `run_kernel_execution_depth_smoke.py`: Kernel execution-depth ownership smoke (memory/scheduler/security stress + lifecycle required-stage readiness).
- `run_operational_soak_recovery_smoke.py`: Long-run operational soak with injected projection-session crash/reconnect and firewall quarantine validation.
- `run_media_engine_contract_smoke.py`: Media/photo engine preflight (FFmpeg/Pillow/OpenCV) plus deterministic runtime contract checks.
- `run_ml_security_sidecar.py`: Optional ML anomaly sidecar (`AXION_ENABLE_ML_SIDECAR=1`).
- `emit_completion_assessment.py`: Emits latest completion/readiness assessment (`out/qa/os_completion_assessment_latest.{json,md}`) with remaining-gap batches.
- `tools/runtime/firmware_os_handoff_enforcement_flow.py`: Firmware->OS contract enforcement (firmware manifest + handoff + smart-driver + Parallel Cubed hardware guard alignment).
- `run_release_gate.ps1`: Aggregated release gate for QA, firmware, reproducibility, and dry-run boot checks.
  - Live boot lane: use `-EnableKernelLiveBoot` (or `-BuildProfile release`) to require `tools/repro/verify_kernel_wsl.ps1` as a gate check.
  - Use `-RequireKernelLiveBoot` to force live boot verification as a critical check regardless of profile.
  - Unified OS+FW lane: use `-EnableUnifiedStackSmoke` (or `-BuildProfile release`) to require top-level `build_axion_stack.ps1` smoke.
  - Use `-RequireUnifiedStackSmoke` to force unified-stack smoke as a critical check regardless of profile.

Installer/module provenance:
- Installer and one-click module intake are fail-closed on signed provenance envelopes.
- Use `build_installer_provenance_envelope(...)` and `build_module_provenance_envelope(...)` from `runtime/shell_ui/apps_host/apps_host.py` for test/QA envelopes.
- Release signing keys are external-source only (no inline key material): set `AXION_KMS_RELEASE_SIGNING_KEY_01` and `AXION_HSM_RELEASE_SIGNING_KEY_02` from your KMS/HSM-backed secret injection before running QA/release gates.
- `run_release_gate.ps1` can resolve signing env values without persisting secrets:
  - `-KmsSigningKeyFile <path> -HsmSigningKeyFile <path>` loads values from local secure files.
  - `-ResolveSigningFromKeyVault -SigningKeyVaultName <vault> -KmsSigningKeySecretName <name> -HsmSigningKeySecretName <name>` pulls from Azure Key Vault (`Az.KeyVault` or `AzureRM.KeyVault` with an authenticated context).
  - `-PromptForSigningKeys` requests masked input and keeps values process-scoped only.
  - `tools/common/provision_release_signing_keys.ps1` auto-provisions strong local key files and sets `AXION_KMS_RELEASE_SIGNING_KEY_01_FILE` / `AXION_HSM_RELEASE_SIGNING_KEY_02_FILE` in user+process scope.

ML sidecar flags:
- `AXION_ENABLE_ML_SIDECAR=1`: enables sidecar execution.
- `AXION_ML_SOURCE_DIR=<path>`: optional override for `entropy_proof_backbone.py` and `autoregressive_next_token.py`.
- `AXION_ML_SIDECAR_ENFORCE=1`: treat anomaly detection as gate-failing.
- `run_release_gate.ps1 -EnableMlSidecar`: enables sidecar in-gate for non-release profiles.
- `run_release_gate.ps1 -RequireMlSidecar`: fail gate if sidecar is skipped/unavailable.
