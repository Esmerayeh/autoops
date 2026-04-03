"""Adaptive baselines and dynamic thresholding helpers."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean, pstdev
from typing import Any


class AdaptiveThresholdEngine:
    """Learn metric baselines from recent history, with time-of-day sensitivity."""

    METRICS = ("cpu", "memory", "disk", "swap")

    def build_profile(self, history: list[dict[str, Any]], snapshot: dict[str, Any]) -> dict[str, Any]:
        hour = int(snapshot["timestamp"][11:13]) if snapshot.get("timestamp") else 0
        hour_bucket = "day" if 8 <= hour < 20 else "night"
        profiled = {"bucket": hour_bucket, "thresholds": {}, "baselines": {}}

        bucketed: dict[str, list[float]] = defaultdict(list)
        for item in history[-240:]:
            ts = item.get("timestamp", "")
            item_hour = int(ts[11:13]) if len(ts) >= 13 and ts[11:13].isdigit() else hour
            item_bucket = "day" if 8 <= item_hour < 20 else "night"
            if item_bucket != hour_bucket:
                continue
            for metric_name in self.METRICS:
                value = item.get("metrics", {}).get(metric_name)
                if isinstance(value, (int, float)):
                    bucketed[metric_name].append(float(value))

        for metric_name in self.METRICS:
            values = bucketed.get(metric_name, [])
            if len(values) < 6:
                values = [
                    float(item.get("metrics", {}).get(metric_name, 0))
                    for item in history[-90:]
                    if isinstance(item.get("metrics", {}).get(metric_name), (int, float))
                ]
            avg = round(mean(values), 2) if values else 0.0
            deviation = round(pstdev(values), 2) if len(values) >= 2 else 5.0
            warning = round(min(95.0, max(avg + deviation * 1.35, avg + 8)), 2)
            critical = round(min(99.0, max(avg + deviation * 2.2, warning + 6)), 2)
            profiled["baselines"][metric_name] = {
                "mean": avg,
                "stddev": deviation,
                "window_size": len(values),
            }
            profiled["thresholds"][metric_name] = {
                "warning": warning,
                "critical": critical,
            }

        process_baselines: dict[str, dict[str, float]] = {}
        process_samples: dict[str, list[float]] = defaultdict(list)
        for item in history[-120:]:
            for proc in item.get("processes", [])[:12]:
                name = (proc.get("name") or "").lower()
                if name:
                    process_samples[name].append(float(proc.get("cpu_percent", 0.0)))
        for name, values in process_samples.items():
            if len(values) < 3:
                continue
            process_baselines[name] = {
                "cpu_mean": round(mean(values), 2),
                "cpu_warning": round(mean(values) + max(5.0, pstdev(values) * 1.5), 2),
            }
        profiled["process_baselines"] = process_baselines
        return profiled
