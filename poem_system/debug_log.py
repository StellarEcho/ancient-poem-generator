"""默认静默的运行记录器；写失败只告警，不影响生成。"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path


class DebugRecorder:
    def __init__(self, enabled: bool = False, root: Path | None = None) -> None:
        self.enabled = enabled
        self.root = Path(root) if root is not None else Path("artifacts") / "runs"

    def save_run(
        self,
        *,
        topic: str,
        source: str,
        poem: dict,
        model_calls: int,
        latency_ms: float,
        model_used: str | None = None,
        raw_model_content: str | None = None,
        model_error: str | None = None,
        model_usage: dict | None = None,
        parse_ok: bool = False,
        local_fix_ok: bool = False,
        local_fix_changed: bool = False,
        validation_errors: list[str] | None = None,
        validation_warnings: list[str] | None = None,
    ) -> Path | None:
        if not self.enabled:
            return None
        run_id = uuid.uuid4().hex[:12]
        run_dir = self.root / time.strftime("%Y%m%d") / run_id
        try:
            run_dir.mkdir(parents=True, exist_ok=True)
            record = {
                "run_id": run_id,
                "topic": topic,
                "source": source,
                "poem": poem,
                "model_calls": model_calls,
                "latency_ms": round(latency_ms, 3),
                "model_used": model_used,
                "raw_model_content": raw_model_content,
                "model_error": model_error,
                "model_usage": model_usage,
                "parse_ok": parse_ok,
                "local_fix_ok": local_fix_ok,
                "local_fix_changed": local_fix_changed,
                "validation_errors": validation_errors or [],
                "validation_warnings": validation_warnings or [],
            }
            target = run_dir / "run.json"
            tmp = target.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps(record, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(target)
            return target
        except Exception:
            # 记录失败绝不能影响生成结果。
            return None
