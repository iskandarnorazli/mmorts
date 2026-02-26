from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def save_snapshot(payload: dict, session_id: str, target_path: str | None = None) -> str:
    Path("snapshots").mkdir(exist_ok=True)
    if target_path:
        path = Path(target_path)
    else:
        stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        path = Path("snapshots") / f"{session_id}_{stamp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)
