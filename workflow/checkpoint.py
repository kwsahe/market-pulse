# workflow/checkpoint.py
# LangGraph 체크포인트 (중간 상태 저장/복구)

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

CHECKPOINT_DIR = Path(__file__).parent.parent / "workflow_checkpoints"
CHECKPOINT_DIR.mkdir(exist_ok=True)

def save_checkpoint(state: dict, run_id: str) -> str:
    """현재 상태를 체크포인트에 저장"""
    filepath = CHECKPOINT_DIR / f"{run_id}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, default=str)
    return str(filepath)

def load_checkpoint(run_id: str) -> Optional[dict]:
    """특정 런 ID 의 체크포인트를 불러옴"""
    filepath = CHECKPOINT_DIR / f"{run_id}.json"
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def delete_checkpoint(run_id: str) -> bool:
    """체크포인트 삭제"""
    filepath = CHECKPOINT_DIR / f"{run_id}.json"
    if filepath.exists():
        filepath.unlink()
        return True
    return False

def list_checkpoints() -> list:
    """저장된 체크포인트 목록 반환"""
    files = sorted(CHECKPOINT_DIR.glob("*.json"), reverse=True)
    return [f.stem for f in files]