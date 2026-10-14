"""Deterministic near real-time replay of raw telemetry segments.

This module turns segments.csv into a replayable telemetry source that
preserves the raw segment boundaries while exposing ML-ready features for
anomaly detection and RCA.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from ..config import settings
from ..processing.feature_extractor import SegmentFeatureExtractor
from ..utils.logger import get_logger, LogContext

logger = get_logger()


@dataclass
class TelemetrySnapshot:
    """A replayed telemetry snapshot for one channel segment."""

    channel: str
    segment_id: int
    timestamp: str
    value: float
    features: Dict[str, float]
    anomaly_label: bool
    raw_points: int


class TelemetryReplayEngine:
    """Replay raw telemetry segments in a deterministic round-robin order."""

    def __init__(self, segments_path: Optional[Path] = None, state_path: Optional[Path] = None):
        self.segments_path = segments_path or (settings.DATA_DIR / settings.SEGMENTS_CSV)
        self.state_path = state_path or (settings.BASE_DIR / "data" / "cache" / "replay_state.json")
        self.feature_extractor = SegmentFeatureExtractor(verbose=False)
        self.segments_df: Optional[pd.DataFrame] = None
        self.channel_segments: Dict[str, List[int]] = {}
        self.channel_positions: Dict[str, int] = {}
        self._load_segments()

    def _load_state(self) -> None:
        """Load replay cursor positions from disk when available."""
        try:
            if not self.state_path.exists():
                return

            with self.state_path.open("r", encoding="utf-8") as f:
                state = json.load(f)

            positions = state.get("channel_positions", {}) if isinstance(state, dict) else {}
            for channel, pos in positions.items():
                if channel not in self.channel_segments:
                    continue
                segments = self.channel_segments[channel]
                if not segments:
                    continue
                try:
                    self.channel_positions[channel] = int(pos) % len(segments)
                except (TypeError, ValueError):
                    self.channel_positions[channel] = 0

            logger.info("✅ Replay cursor state restored")
        except Exception as exc:
            logger.warning(f"⚠️ Unable to restore replay cursor state: {exc}")

    def _save_state(self) -> None:
        """Persist replay cursor positions to disk."""
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "updated_at": datetime.now().isoformat(),
                "channel_positions": self.channel_positions,
            }
            with self.state_path.open("w", encoding="utf-8") as f:
                json.dump(payload, f)
        except Exception as exc:
            logger.warning(f"⚠️ Unable to persist replay cursor state: {exc}")

    def _load_segments(self) -> None:
        with LogContext("Loading raw telemetry for replay", file=str(self.segments_path.name)):
            if not self.segments_path.exists():
                raise FileNotFoundError(f"segments.csv not found: {self.segments_path}")

            df = pd.read_csv(self.segments_path)
            required = {"segment", "channel", "timestamp", "value"}
            missing = required - set(df.columns)
            if missing:
                raise ValueError(f"segments.csv missing required columns: {sorted(missing)}")

            df = df.copy()
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            df = df.dropna(subset=["segment", "channel", "value"])
            df["segment"] = df["segment"].astype(int)
            df["channel"] = df["channel"].astype(str)
            df = df.sort_values(["channel", "segment", "timestamp"])

            self.segments_df = df.reset_index(drop=True)
            self.channel_segments.clear()
            self.channel_positions.clear()

            for channel, channel_df in self.segments_df.groupby("channel"):
                ordered_segments = channel_df["segment"].drop_duplicates().tolist()
                self.channel_segments[str(channel)] = ordered_segments
                self.channel_positions[str(channel)] = 0

            self._load_state()

            logger.info(
                f"✅ Replay engine loaded {len(self.segments_df)} raw readings across {len(self.channel_segments)} channels"
            )

    def available_channels(self) -> List[str]:
        return sorted(self.channel_segments.keys())

    def _next_segment_id(self, channel: str) -> Optional[int]:
        segments = self.channel_segments.get(channel, [])
        if not segments:
            return None

        position = self.channel_positions.get(channel, 0)
        segment_id = segments[position % len(segments)]
        self.channel_positions[channel] = (position + 1) % len(segments)
        return segment_id

    def _build_snapshot(self, channel: str, segment_id: int) -> TelemetrySnapshot:
        if self.segments_df is None:
            raise RuntimeError("Replay engine not loaded")

        segment_df = self.segments_df[
            (self.segments_df["channel"] == channel) & (self.segments_df["segment"] == segment_id)
        ].copy()

        if segment_df.empty:
            raise ValueError(f"No raw readings found for channel={channel}, segment={segment_id}")

        segment_df = segment_df.sort_values("timestamp")
        values = segment_df["value"].to_numpy()
        timestamps = segment_df["timestamp"].tolist() if "timestamp" in segment_df.columns else None

        features = self.feature_extractor.extract_features_from_segment(
            values=values,
            timestamps=timestamps,
            segment_id=segment_id,
            channel=channel,
        )

        anomaly_label = bool(int(segment_df["anomaly"].iloc[0])) if "anomaly" in segment_df.columns else False
        raw_timestamp = segment_df["timestamp"].iloc[-1] if timestamps else datetime.now()
        timestamp = raw_timestamp.isoformat() if hasattr(raw_timestamp, "isoformat") else str(raw_timestamp)

        return TelemetrySnapshot(
            channel=channel,
            segment_id=segment_id,
            timestamp=timestamp,
            value=float(segment_df["value"].mean()),
            features=features,
            anomaly_label=anomaly_label,
            raw_points=len(segment_df),
        )

    def next_snapshot(self, include_all_channels: bool = True) -> Dict:
        """Return the next deterministic snapshot for the selected channel set."""
        channel_pool = self.available_channels()
        if not include_all_channels:
            channel_pool = [ch for ch in settings.MAGNETOMETER_CHANNELS if ch in self.channel_segments]

        if not channel_pool:
            raise ValueError("No channels available for replay")

        snapshots: List[TelemetrySnapshot] = []
        for channel in channel_pool:
            segment_id = self._next_segment_id(channel)
            if segment_id is None:
                continue
            snapshots.append(self._build_snapshot(channel, segment_id))

        self._save_state()

        if not snapshots:
            raise ValueError("No telemetry snapshots available")

        primary = next((snap for snap in snapshots if snap.channel in settings.MAGNETOMETER_CHANNELS), snapshots[0])
        now_iso = datetime.now().isoformat()

        return {
            "timestamp": now_iso,
            "source": "segments.csv",
            "mode": "all_channels" if include_all_channels else "magnetometer_only",
            "sampled_segment": primary.segment_id,
            "channels": [
                {
                    "channel": snap.channel,
                    "segment": snap.segment_id,
                    "timestamp": snap.timestamp,
                    "value": snap.value,
                    "features": snap.features,
                    "dataset_anomaly": snap.anomaly_label,
                    "raw_points": snap.raw_points,
                }
                for snap in snapshots
            ],
            "current_features": primary.features,
            "dataset_anomaly": primary.anomaly_label,
        }
