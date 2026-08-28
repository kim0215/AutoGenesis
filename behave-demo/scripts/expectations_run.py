#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Expectations baseline capture / verify entry for Android|iOS → HarmonyOS evaluation.

Examples:
  uv run python scripts/expectations_run.py capture --source android
  uv run python scripts/expectations_run.py verify --target harmonyos
  uv run python scripts/expectations_run.py all --source android --target harmonyos
  uv run python scripts/expectations_run.py verify --target harmonyos --feature features/
  uv run python scripts/expectations_run.py verify --target harmonyos \\
      --feature features/WeatherSettings.feature --feature features/LocationSearch.feature

Capture does NOT require this script specifically: any behave run with
EXPECTATIONS_MODE=capture (and Android steps calling update_expectation) will
refresh expectations/<stem>_expectations.json. This script only sets env and
invokes behave.

Full pipeline including Android/HarmonyOS *code generation* is orchestrated by
skill `.github/skills/expectations-migration-run` (mode=full), which calls this
script for capture/verify segments only.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

BEHAVE_DEMO = Path(__file__).resolve().parents[1]

MCP_BY_PLATFORM = {
    "android": "auto-genesis-mcp-mobile",
    "ios": "auto-genesis-mcp-ios",
    "harmonyos": "auto-genesis-mcp-harmonyos",
}


def expand_feature_args(values: list[str], *, base: Path) -> list[str]:
    """Expand --feature values into behave paths (file, dir of *.feature, comma list)."""
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        for part in value.split(","):
            part = part.strip().strip('"').strip("'")
            if not part:
                continue
            path = Path(part)
            if not path.is_absolute():
                path = (base / path).resolve()
            else:
                path = path.resolve()
            if path.is_dir():
                files = sorted(path.glob("*.feature"))
                if not files:
                    raise SystemExit(f"[expectations_run] no .feature files in {path}")
            elif path.is_file():
                files = [path]
            else:
                raise SystemExit(f"[expectations_run] feature not found: {part}")
            for file in files:
                key = str(file)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    rel = file.relative_to(base)
                    out.append(str(rel).replace("\\", "/"))
                except ValueError:
                    out.append(str(file))
    return out


def _run_behave(
    *,
    mode: str,
    features: list[str],
    source: str,
    target: str,
    name: str | None,
    extra: list[str],
) -> int:
    """Run Features one behave process at a time on the same device.

    Each process loads only that file's ``*_steps.py`` (FEATURE_STEM=stem).
    Loading every module into one process makes duplicate @given/@when text
    raise AmbiguousStep and abort the rest of the later module.
    """
    rcs: list[int] = []
    total = len(features)
    for i, feature in enumerate(features, 1):
        env = os.environ.copy()
        env["EXPECTATIONS_MODE"] = mode
        # Always this file's stem — ignore a comma-joined FEATURE_STEM from parent.
        env["FEATURE_STEM"] = Path(feature).stem
        if mode == "capture":
            env["SOURCE_PLATFORM"] = source
            env["AUTO_GENESIS_MCP_SERVER"] = MCP_BY_PLATFORM[source]
            env.pop("TARGET_PLATFORM", None)
        else:
            env["TARGET_PLATFORM"] = target
            env["AUTO_GENESIS_MCP_SERVER"] = MCP_BY_PLATFORM[target]
            env.pop("SOURCE_PLATFORM", None)

        cmd = [sys.executable, "-m", "behave", feature, "-f", "plain"]
        if name:
            cmd.extend(["--name", name])
        cmd.extend(extra)

        print("=" * 60)
        print(f"[expectations_run] mode={mode}  feature {i}/{total}")
        print(f"[expectations_run] cwd={BEHAVE_DEMO}")
        print(f"[expectations_run] MCP={env['AUTO_GENESIS_MCP_SERVER']}")
        print(f"[expectations_run] FEATURE_STEM={env.get('FEATURE_STEM')}")
        print(f"[expectations_run] features={[feature]}")
        if mode == "capture":
            print(f"[expectations_run] SOURCE_PLATFORM={source}")
        else:
            print(f"[expectations_run] TARGET_PLATFORM={target}")
        print(f"[expectations_run] cmd={' '.join(cmd)}")
        print("=" * 60)

        rc = subprocess.call(cmd, cwd=str(BEHAVE_DEMO), env=env)
        rcs.append(rc)
        if rc != 0:
            print(
                f"[expectations_run] {feature} finished with exit code {rc} "
                f"({i}/{total}); continuing to next Feature"
            )

    failed = [rc for rc in rcs if rc != 0]
    return failed[0] if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run expectations baseline capture (source) and/or verify (target) "
            "for migration evaluation."
        )
    )
    parser.add_argument(
        "mode",
        choices=("capture", "verify", "all"),
        help=(
            "capture=refresh expectations from source; "
            "verify=target vs expectations; all=capture then verify"
        ),
    )
    parser.add_argument(
        "--feature",
        action="append",
        dest="features",
        default=None,
        help=(
            "Feature file, directory of *.feature, or comma-separated list. "
            "Repeatable. Default: features/weather.feature"
        ),
    )
    parser.add_argument(
        "--source",
        default="android",
        choices=sorted(p for p in MCP_BY_PLATFORM if p != "harmonyos"),
        help="Source platform for capture (default: android)",
    )
    parser.add_argument(
        "--target",
        default="harmonyos",
        choices=("harmonyos",),
        help="Target platform for verify (default: harmonyos / Cangjie)",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Optional behave --name scenario filter",
    )
    parser.add_argument(
        "behave_args",
        nargs="*",
        help="Extra args passed through to behave",
    )
    args = parser.parse_args(argv)
    features = expand_feature_args(
        args.features or ["features/weather.feature"],
        base=BEHAVE_DEMO,
    )

    if args.mode in ("capture", "all"):
        rc = _run_behave(
            mode="capture",
            features=features,
            source=args.source,
            target=args.target,
            name=args.name,
            extra=args.behave_args,
        )
        if rc != 0:
            print(f"[expectations_run] capture failed with exit code {rc}")
            return rc
        print("[expectations_run] capture finished OK")
        print(
            f"[expectations_run] expectations file: "
            f"{BEHAVE_DEMO / 'expectations' / 'weather_expectations.json'}"
        )

    if args.mode in ("verify", "all"):
        rc = _run_behave(
            mode="verify",
            features=features,
            source=args.source,
            target=args.target,
            name=args.name,
            extra=args.behave_args,
        )
        if rc != 0:
            print(f"[expectations_run] verify failed with exit code {rc}")
            return rc
        print("[expectations_run] verify finished OK")
        print(
            f"[expectations_run] report: "
            f"{BEHAVE_DEMO / 'expectations' / 'weather_verify_report.json'}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
