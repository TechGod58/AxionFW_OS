from pathlib import Path

from generate_smart_driver_handoff import generate_smart_driver_handoff


def test_generate_smart_driver_handoff(tmp_path):
    state_path = tmp_path / "smart_driver_fabric_state.json"
    registry_path = tmp_path / "smart_driver_fabric_artifact_registry.json"
    header_path = tmp_path / "smart_driver_handoff.h"
    out_path = tmp_path / "smart_driver_kernel_handoff.json"

    state_path.write_text(
        (
            "{\n"
            '  "ready": true,\n'
            '  "load_once_token": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",\n'
            '  "target_bsp_id": "bsp_q35_ovmf_ref_v1",\n'
            '  "target_family": "q35",\n'
            '  "resolved_driver_ids": ["drv_a", "drv_b"],\n'
            '  "synthesized_drivers": [{"driver_id": "drv_s"}]\n'
            "}\n"
        ),
        encoding="utf-8",
    )
    registry_path.write_text(
        (
            "{\n"
            '  "version": 1,\n'
            '  "artifacts": [\n'
            '    {"driver_id": "drv_s", "status": "compiled_signed_verified"}\n'
            "  ]\n"
            "}\n"
        ),
        encoding="utf-8",
    )

    result = generate_smart_driver_handoff(
        state_path=state_path,
        artifact_registry_path=registry_path,
        header_path=header_path,
        out_path=out_path,
    )
    assert result["ok"] is True
    assert result["code"] == "SMART_DRIVER_KERNEL_HANDOFF_READY"
    assert header_path.exists()
    assert out_path.exists()
    text = header_path.read_text(encoding="utf-8")
    assert "AX_SDF_HANDOFF_READY" in text
    assert "AX_SDF_HANDOFF_SIGNED_ARTIFACTS_TOTAL ((uint64_t)1u)" in text
