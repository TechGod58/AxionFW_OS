import sys
from pathlib import Path

PROMOTION_DIR = Path(__file__).resolve().parents[1]
if str(PROMOTION_DIR) not in sys.path:
    sys.path.insert(0, str(PROMOTION_DIR))

