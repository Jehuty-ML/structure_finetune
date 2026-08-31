#!/usr/bin/env python3
"""打磨已有 train/val 中的攻击旁白。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from polish_quest_attack_say import polish_attack_row


def main() -> None:
    data_dir = ROOT / "examples" / "quest" / "sample_data"
    for name in ("train.json", "val.json", "train_sample.json"):
        path = data_dir / name
        if not path.exists():
            continue
        rows = json.loads(path.read_text(encoding="utf-8"))
        rows = [polish_attack_row(r) for r in rows]
        path.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        n = sum(1 for r in rows if r.get("meta", {}).get("rule_id") == "combat_attack")
        print(f"{name}: polished attack={n} total={len(rows)}")


if __name__ == "__main__":
    main()
