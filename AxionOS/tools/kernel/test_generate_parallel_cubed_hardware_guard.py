import json
from pathlib import Path

from generate_parallel_cubed_hardware_guard import generate_parallel_cubed_hardware_guard


def test_generate_parallel_cubed_hardware_guard_masks(tmp_path: Path):
    policy = {
        "enabled": True,
        "strictMode": True,
        "inventoryRequiredBeforeSmartWrite": True,
        "allowBusClasses": [1, 2, 6],
        "denyBusClasses": [12, 13],
    }
    policy_path = tmp_path / "PARALLEL_CUBED_HARDWARE_GUARD_V1.json"
    policy_path.write_text(json.dumps(policy) + "\n", encoding="utf-8")

    header_path = tmp_path / "parallel_cubed_hardware_guard.h"
    out_path = tmp_path / "parallel_cubed_hardware_guard.json"

    out = generate_parallel_cubed_hardware_guard(
        policy_path=policy_path,
        header_path=header_path,
        out_path=out_path,
    )

    assert out["ok"] is True
    assert out["payload"]["enabled"] == 1
    assert out["payload"]["strict_mode"] == 1
    # allow: bits 1,2,6 => 0x46
    assert out["payload"]["allow_mask"] == 0x46
    # deny: bits 12,13 => 0x3000
    assert out["payload"]["deny_mask"] == 0x3000
    assert header_path.exists()
    assert out_path.exists()
