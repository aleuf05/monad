"""Phase 2A descriptive evaluator; advanced GAM/latent models remain deferred."""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from monad_zero.organism import TELEMETRY_FIELDS


@dataclass(frozen=True)
class EvaluationResult:
    model_class: str
    n: int
    log_likelihood: float
    metrics: dict[str, float]

    def as_dict(self) -> dict[str, Any]:
        return {"model_class": self.model_class, "n": self.n, "log_likelihood": self.log_likelihood, "metrics": self.metrics}


class StatisticalEvaluator:
    """Ingest, validate, and fit lightweight M0/M2 models without dependencies."""

    def ingest(self, records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = [record for record in records if "nexus_closure_index" in record]
        missing = [field for row in rows for field in TELEMETRY_FIELDS if field not in row]
        if missing:
            raise ValueError(f"telemetry schema missing fields: {sorted(set(missing))}")
        return rows

    def fit(self, records: Iterable[dict[str, Any]], model_class: str = "M0") -> EvaluationResult:
        rows = self.ingest(records)
        if model_class not in {"M0", "M1", "M2", "M3"}:
            raise ValueError("model_class must be M0, M1, M2, or M3")
        ys = [float(row["nexus_closure_index"]) for row in rows]
        if not ys:
            return EvaluationResult(model_class, 0, 0.0, {})
        if model_class == "M0":
            predictions = [sum(ys) / len(ys)] * len(ys)
        elif model_class == "M1":
            predictions = [sum(ys[max(0, i - 2):i + 3]) / len(ys[max(0, i - 2):i + 3]) for i in range(len(ys))]
        elif model_class == "M2":
            midpoint = len(ys) // 2
            left, right = ys[:midpoint] or ys, ys[midpoint:] or ys
            predictions = [sum(left) / len(left)] * midpoint + [sum(right) / len(right)] * (len(ys) - midpoint)
        else:
            threshold = sum(ys) / len(ys)
            predictions = [threshold if value < threshold else max(ys) for value in ys]
        residuals = [actual - predicted for actual, predicted in zip(ys, predictions)]
        variance = max(1e-9, sum(value * value for value in residuals) / len(residuals))
        ll = -0.5 * sum((residual * residual) / variance + math.log(2 * math.pi * variance) for residual in residuals)
        return EvaluationResult(model_class, len(rows), round(ll, 6), {"rmse": round(math.sqrt(variance), 6), "mean_closure": round(sum(ys) / len(ys), 6)})

    def hysteresis_width(self, records: Iterable[dict[str, Any]], threshold: float = 0.5) -> float | None:
        rows = sorted(self.ingest(records), key=lambda row: row["tick"])
        forward = [row for row in rows if row["sweep_direction"] == "FORWARD"]
        reverse = [row for row in rows if row["sweep_direction"] == "REVERSE"]
        def crossing(group):
            for row in group:
                if row["nexus_closure_index"] >= threshold:
                    return float(row["q"])
            return None
        entry, exit = crossing(forward), crossing(reverse)
        return None if entry is None or exit is None else round(exit - entry, 6)

    def regime_summary(self, records: Iterable[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for row in self.ingest(records):
            counts[row["state_regime_estimate"] or "unknown"] += 1
        return dict(counts)
