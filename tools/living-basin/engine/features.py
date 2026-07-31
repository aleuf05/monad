"""Registry of inspectable emergent features.

A feature is created the moment its formation threshold is crossed (never
placed by hand). Its origin (`genesis_tick`, `causal_event_ids`) is fixed at
creation and never rewritten; later events may be appended to
`causal_event_ids` as the feature evolves, and `current_status` may change,
but the genesis is permanent.

A single cell can carry more than one feature over time -- a hollow can be a
WaterPool first and later, as the same inflow undercuts it, an ErosiveGully
too. Feature *type* (not raw cell occupancy) is what guards against
duplicate creation, tracked per (cell, feature_type).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class Feature:
    feature_id: str
    feature_type: str  # WaterPool | HerbivoreTrail | GrazedPatch | ErosiveGully
    cells: list[list[int]]
    genesis_tick: int
    current_status: str = "Stable"
    causal_event_ids: list[str] = field(default_factory=list)
    authored_override: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class FeatureRegistry:
    def __init__(self):
        self._features: dict[str, Feature] = {}
        self._by_cell: dict[tuple[int, int], list[str]] = {}
        self._by_cell_type: dict[tuple[tuple[int, int], str], str] = {}
        self._counters: dict[str, int] = {}

    def _new_id(self, feature_type: str) -> str:
        key = feature_type.lower()
        self._counters[key] = self._counters.get(key, 0) + 1
        return f"feature_{key}_{self._counters[key]:04d}"

    def feature_of_type_at(self, cell: tuple[int, int], feature_type: str) -> Feature | None:
        fid = self._by_cell_type.get((cell, feature_type))
        return self._features.get(fid) if fid else None

    def features_at(self, cell: tuple[int, int]) -> list[Feature]:
        return [self._features[fid] for fid in self._by_cell.get(cell, [])]

    def feature_at(self, cell: tuple[int, int]) -> Feature | None:
        """Most recently created feature at this cell, or None. Used for
        click/hover diagnostics when the caller doesn't care which type."""
        feats = self.features_at(cell)
        return feats[-1] if feats else None

    def get(self, feature_id: str) -> Feature | None:
        return self._features.get(feature_id)

    def all(self) -> list[Feature]:
        return list(self._features.values())

    def create(
        self,
        feature_type: str,
        cells: list[tuple[int, int]],
        genesis_tick: int,
        genesis_event_id: str,
    ) -> Feature:
        feat = Feature(
            feature_id=self._new_id(feature_type),
            feature_type=feature_type,
            cells=[list(c) for c in cells],
            genesis_tick=genesis_tick,
            causal_event_ids=[genesis_event_id],
        )
        self._features[feat.feature_id] = feat
        for c in cells:
            self._by_cell.setdefault(c, []).append(feat.feature_id)
            self._by_cell_type[(c, feature_type)] = feat.feature_id
        return feat

    def append_event(self, feature_id: str, event_id: str) -> None:
        feat = self._features[feature_id]
        if event_id not in feat.causal_event_ids:
            feat.causal_event_ids.append(event_id)

    def mark_override(self, feature_id: str) -> None:
        self._features[feature_id].authored_override = True

    def to_dict(self) -> dict:
        return {fid: f.to_dict() for fid, f in self._features.items()}
