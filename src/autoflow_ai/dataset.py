from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from autoflow_ai.schemas import AIRun, ModelCall, RunOutcome, ToolCall


@dataclass(frozen=True)
class AIDataset:
    runs: Sequence[AIRun]


def load_jsonl_dataset(path: str | Path) -> AIDataset:
    p = Path(path)
    runs: list[AIRun] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            raw = json.loads(line)

            tool_calls = tuple(
                ToolCall(
                    tool=str(tc["tool"]),
                    latency_ms=float(tc.get("latency_ms", 0.0)),
                    success=bool(tc.get("success", True)),
                    error_type=tc.get("error_type"),
                )
                for tc in raw.get("tool_calls", [])
            )

            model_calls = tuple(
                ModelCall(
                    model=str(mc["model"]),
                    latency_ms=float(mc.get("latency_ms", 0.0)),
                    input_tokens=int(mc.get("input_tokens", 0)),
                    output_tokens=int(mc.get("output_tokens", 0)),
                )
                for mc in raw.get("model_calls", [])
            )

            outcome_raw = raw.get("outcome", {}) or {}
            outcome = RunOutcome(
                success=bool(outcome_raw.get("success", True)),
                human_override=bool(outcome_raw.get("human_override", False)),
                quality_score=outcome_raw.get("quality_score"),
                cost_usd=outcome_raw.get("cost_usd"),
            )

            runs.append(
                AIRun(
                    run_id=str(raw["run_id"]),
                    workflow_id=str(raw["workflow_id"]),
                    tool_calls=tool_calls,
                    model_calls=model_calls,
                    outcome=outcome,
                    attributes=dict(raw.get("attributes", {})),
                )
            )

    return AIDataset(runs=tuple(runs))