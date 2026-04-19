from pathlib import Path
import shutil


def move_to_quarantine(src_path, quarantine_dir):
    q = Path(quarantine_dir)
    q.mkdir(parents=True, exist_ok=True)
    dst = q / Path(src_path).name
    shutil.move(src_path, dst)
    return str(dst)


def move_to_target(src_path, target_path):
    t = Path(target_path)
    t.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(src_path, t)
    return str(t)
