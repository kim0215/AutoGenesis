# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Read/write expectations JSON and per-scenario verify reports."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

BEHAVE_DEMO = Path(__file__).resolve().parents[1]
EXPECTATIONS_DIR = BEHAVE_DEMO / "expectations"
TZ_CST = timezone(timedelta(hours=8))

_verify_report: dict[str, Any] = {}


def _now_iso() -> str:
    return datetime.now(TZ_CST).replace(microsecond=0).isoformat()


def default_expectations_path(feature: str | None = None) -> Path:
    stem = Path(feature or os.environ.get("FEATURE_STEM") or "weather").stem
    stem = "".join(c if c.isalnum() or c == "_" else "_" for c in stem) or "weather"
    return EXPECTATIONS_DIR / f"{stem}_expectations.json"


def _empty_doc(platform: str, feature: str | None, scenario: str | None) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "source": {
            "platform": platform,
            "captured_at": _now_iso(),
            "feature": feature or "",
            "scenario": scenario or "",
        },
        "expectations": {},
    }


def update_expectation(
    key: str,
    value: Any = None,
    *,
    kind: str = "text_equals",
    level: str = "soft",
    platform: str = "android",
    feature: str | None = None,
    scenario: str | None = None,
    path: str | Path | None = None,
) -> None:
    dest = Path(path) if path else default_expectations_path(feature)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        try:
            doc = json.loads(dest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            doc = _empty_doc(platform, feature, scenario)
    else:
        doc = _empty_doc(platform, feature, scenario)
    doc.setdefault("schema_version", 1)
    source = doc.setdefault("source", {})
    source["platform"] = platform
    source["captured_at"] = _now_iso()
    if feature:
        source["feature"] = feature
    if scenario:
        source["scenario"] = scenario
    expectations = doc.setdefault("expectations", {})
    expectations[key] = {"value": value, "level": level, "kind": kind}
    dest.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def reset_verify_report(*, platform: str, scenario: str) -> None:
    global _verify_report
    _verify_report = {
        "platform": platform,
        "scenario": scenario,
        "hard_results": [],
        "soft_drifts": [],
        "behave_status": "",
    }


def add_hard_result(key: str, *, status: str, detail: str = "") -> None:
    _verify_report.setdefault("hard_results", []).append(
        {"key": key, "status": status, "detail": detail}
    )


def add_soft_drift(key: str, *, expected=None, actual=None, note: str = "") -> None:
    _verify_report.setdefault("soft_drifts", []).append(
        {"key": key, "expected": expected, "actual": actual, "note": note}
    )


def set_behave_status(status: str) -> None:
    _verify_report["behave_status"] = status


def save_verify_report(path: str | Path | None = None) -> Path:
    scenario = str(_verify_report.get("scenario") or "unknown")
    slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in scenario)
    stem = (os.environ.get("FEATURE_STEM") or "weather").split(",")[0].strip() or "weather"
    dest = Path(path) if path else (
        EXPECTATIONS_DIR / "scenario_reports" / stem / f"{slug}_verify_report.json"
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(_verify_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return dest
