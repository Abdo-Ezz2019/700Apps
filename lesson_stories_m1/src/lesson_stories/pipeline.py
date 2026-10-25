"""Glue for the integration: run S0 then S1 and write intake.json + brief.json."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from . import s0_intake, s1_brief
from .llm import LLMClient
from .models import Brief, Intake, Request


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_module1(request: Union[Request, Dict[str, Any]], tts_supported_dialects: List[str],
                llm: LLMClient, db: sqlite3.Connection, out_dir: Optional[Path] = None,
                now: Optional[datetime] = None) -> Tuple[Intake, Brief]:
    """S0 -> S1. If `out_dir` is given, writes intake.json and brief.json there."""
    intake = s0_intake.run(request, tts_supported_dialects, llm)
    brief = s1_brief.run(intake.country, intake.language, intake.dialect_applied,
                         intake.age_group, llm, db, now=now)
    if out_dir is not None:
        write_json(Path(out_dir) / "intake.json", intake.to_dict())
        write_json(Path(out_dir) / "brief.json", brief.to_dict())
    return intake, brief
