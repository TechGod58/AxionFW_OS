from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def detect_device(bus: str, vendor: str, product: str, cls: str = "unknown"):
    return {
        "corr": f"corr_dev_{bus}_{vendor}_{product}",
        "bus": bus,
        "vendor": vendor,
        "product": product,
        "class": cls,
        "ts": now_iso()
    }
