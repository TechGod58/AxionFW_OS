#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fw_rewrite_engine import FW_BASE, build_capability_graph, find_latest_json, load_json, save_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Build vendor-agnostic hardware capability graph for rewrite planning")
    parser.add_argument("--inventory", default="", help="Inventory manifest path. Defaults to latest out/manifests/*.json")
    parser.add_argument("--primitive-catalog", default="", help="Primitive catalog json path")
    parser.add_argument("--adapter-contract", default="", help="Chipset bus adapter contract json path")
    parser.add_argument("--out", default="", help="Output graph path")
    args = parser.parse_args()

    inventory_path = Path(args.inventory).resolve() if str(args.inventory).strip() else find_latest_json(FW_BASE / "out" / "manifests")
    primitive_path = (
        Path(args.primitive_catalog).resolve()
        if str(args.primitive_catalog).strip()
        else (FW_BASE / "policy" / "hardware_rewrite_primitive_catalog_v1.json")
    )
    adapter_path = (
        Path(args.adapter_contract).resolve()
        if str(args.adapter_contract).strip()
        else (FW_BASE / "policy" / "chipset_bus_adapter_contract_v1.json")
    )

    inventory = load_json(inventory_path, {})
    primitive_catalog = load_json(primitive_path, {})
    adapter_contract = load_json(adapter_path, {})
    if not isinstance(inventory, dict) or not inventory:
        raise SystemExit(f"Invalid inventory payload: {inventory_path}")
    if not isinstance(primitive_catalog, dict) or not primitive_catalog:
        raise SystemExit(f"Invalid primitive catalog payload: {primitive_path}")
    if not isinstance(adapter_contract, dict) or not adapter_contract:
        raise SystemExit(f"Invalid adapter contract payload: {adapter_path}")

    inventory["source_path"] = str(inventory_path)
    graph = build_capability_graph(
        inventory=inventory,
        primitive_catalog=primitive_catalog,
        adapter_contract=adapter_contract,
    )
    out_path = Path(args.out).resolve() if str(args.out).strip() else (FW_BASE / "out" / "rewrite" / "capability_graph_v1.json")
    save_json(out_path, graph)
    save_json(out_path.parent / "latest_capability_graph.json", graph)

    result = {
        "ok": True,
        "code": "AXION_FW_CAPABILITY_GRAPH_READY",
        "inventory_path": str(inventory_path),
        "primitive_catalog_path": str(primitive_path),
        "adapter_contract_path": str(adapter_path),
        "graph_path": str(out_path),
        "adapter_id": str(((graph.get("adapter_selection") or {}).get("adapter_id") or "")),
        "auto_mapped_unknown_board": bool(((graph.get("adapter_selection") or {}).get("auto_mapped_unknown_board"))),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

