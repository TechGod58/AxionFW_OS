#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def first_name(entries, key):
    vals = []
    for entry in ensure_list(entries):
        value = entry.get(key)
        if value is not None:
            vals.append(str(value))
    return vals


def filter_physical_network(entries):
    kept = []
    for entry in ensure_list(entries):
        pnp = str(entry.get("PNPDeviceID") or "")
        name = str(entry.get("Name") or "")
        lower = name.lower()
        if pnp.startswith("PCI\\") or pnp.startswith("USB\\"):
            if "virtual" not in lower and "miniport" not in lower and "kernel debug" not in lower:
                kept.append(entry)
    return kept


def summarize(inv):
    system = ensure_list(inv.get("computer_system"))
    bios = ensure_list(inv.get("bios"))
    cpu = ensure_list(inv.get("processor"))
    disks = ensure_list(inv.get("disk_drives"))
    net = filter_physical_network(inv.get("network_adapters"))
    video = ensure_list(inv.get("video_controllers"))
    audio = ensure_list(inv.get("sound_devices"))
    keyboard = ensure_list(inv.get("keyboards"))
    pointing = ensure_list(inv.get("pointing_devices"))
    battery = ensure_list(inv.get("battery"))

    return {
        "manufacturer": first_name(system, "Manufacturer"),
        "model": first_name(system, "Model"),
        "system_family": first_name(system, "SystemFamily"),
        "bios_vendor": first_name(bios, "Manufacturer"),
        "bios_version": first_name(bios, "SMBIOSBIOSVersion"),
        "cpu": first_name(cpu, "Name"),
        "storage_models": sorted({str(entry.get("Model")) for entry in disks if entry.get("Model")}),
        "storage_interfaces": sorted({str(entry.get("InterfaceType")) for entry in disks if entry.get("InterfaceType")}),
        "network": sorted({str(entry.get("Name")) for entry in net if entry.get("Name")}),
        "video": sorted({str(entry.get("Name")) for entry in video if entry.get("Name")}),
        "audio": sorted({str(entry.get("Name")) for entry in audio if entry.get("Name")}),
        "keyboards": sorted({str(entry.get("Description") or entry.get("Name")) for entry in keyboard if entry.get("Description") or entry.get("Name")}),
        "pointing_devices": sorted({str(entry.get("Description") or entry.get("Name")) for entry in pointing if entry.get("Description") or entry.get("Name")}),
        "battery_present": bool(battery),
    }


def intersection(values_a, values_b):
    return sorted(set(values_a) & set(values_b))


def union(values_a, values_b):
    return sorted(set(values_a) | set(values_b))


def build_matrix(left_path: Path, right_path: Path):
    left = load(left_path)
    right = load(right_path)
    left_summary = summarize(left)
    right_summary = summarize(right)

    matrix = {
        "matrix_id": "first_laptop_family_bringup_matrix_v1",
        "generated_utc": now(),
        "inputs": [str(left_path), str(right_path)],
        "systems": [
            {
                "source": str(left_path),
                "manufacturer": left_summary["manufacturer"],
                "model": left_summary["model"],
                "storage": left_summary["storage_models"],
                "network": left_summary["network"],
                "video": left_summary["video"],
                "input": {
                    "keyboards": left_summary["keyboards"],
                    "pointing_devices": left_summary["pointing_devices"]
                }
            },
            {
                "source": str(right_path),
                "manufacturer": right_summary["manufacturer"],
                "model": right_summary["model"],
                "storage": right_summary["storage_models"],
                "network": right_summary["network"],
                "video": right_summary["video"],
                "input": {
                    "keyboards": right_summary["keyboards"],
                    "pointing_devices": right_summary["pointing_devices"]
                }
            }
        ],
        "common_ground": {
            "storage_interfaces": intersection(left_summary["storage_interfaces"], right_summary["storage_interfaces"]),
            "network": intersection(left_summary["network"], right_summary["network"]),
            "video": intersection(left_summary["video"], right_summary["video"]),
            "keyboards": intersection(left_summary["keyboards"], right_summary["keyboards"]),
            "pointing_devices": intersection(left_summary["pointing_devices"], right_summary["pointing_devices"])
        },
        "combined_targets": {
            "storage": union(left_summary["storage_models"], right_summary["storage_models"]),
            "network": union(left_summary["network"], right_summary["network"]),
            "video": union(left_summary["video"], right_summary["video"]),
            "audio": union(left_summary["audio"], right_summary["audio"]),
            "input_keyboards": union(left_summary["keyboards"], right_summary["keyboards"]),
            "input_pointing_devices": union(left_summary["pointing_devices"], right_summary["pointing_devices"])
        },
        "bringup_workstreams": [
            {
                "area": "storage",
                "goal": "Boot and read internal system storage safely.",
                "targets": union(left_summary["storage_models"], right_summary["storage_models"]),
                "status": "pending"
            },
            {
                "area": "input",
                "goal": "Ensure internal keyboard and pointing devices are usable in pre-boot and OS bring-up.",
                "targets": union(left_summary["keyboards"], right_summary["keyboards"]) + union(left_summary["pointing_devices"], right_summary["pointing_devices"]),
                "status": "pending"
            },
            {
                "area": "display",
                "goal": "Bring up stable console/framebuffer output on real laptop graphics hardware.",
                "targets": union(left_summary["video"], right_summary["video"]),
                "status": "pending"
            },
            {
                "area": "network",
                "goal": "Reach basic wired or fallback network bring-up after storage/input/display are stable.",
                "targets": union(left_summary["network"], right_summary["network"]),
                "status": "pending"
            }
        ]
    }
    return matrix


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("left_inventory")
    parser.add_argument("right_inventory")
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--md-out", required=True)
    args = parser.parse_args()

    matrix = build_matrix(Path(args.left_inventory), Path(args.right_inventory))
    json_out = Path(args.json_out)
    md_out = Path(args.md_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# First Laptop Family Bring-Up Matrix",
        "",
        f"Generated: {matrix['generated_utc']}",
        "",
        "## Systems",
    ]
    for system in matrix["systems"]:
        label = ", ".join(system.get("model") or [system["source"]])
        lines.append(f"- {label}")
        lines.append(f"  source: {system['source']}")
        lines.append(f"  storage: {', '.join(system['storage']) if system['storage'] else 'none detected'}")
        lines.append(f"  network: {', '.join(system['network']) if system['network'] else 'none detected'}")
        lines.append(f"  video: {', '.join(system['video']) if system['video'] else 'none detected'}")
    lines.extend(["", "## Workstreams"])
    for item in matrix["bringup_workstreams"]:
        targets = ", ".join(item["targets"]) if item["targets"] else "pending inventory"
        lines.append(f"- {item['area']}: {item['goal']} Targets: {targets}")
    md_out.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
