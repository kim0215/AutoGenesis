# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Load platform step modules (one or more, to avoid loading the wrong app).

Env:
  EXPECTATIONS_MODE=capture|verify   (default: verify)
  SOURCE_PLATFORM=android|ios  (capture; default android)
  TARGET_PLATFORM=harmonyos    (verify; default harmonyos)
  FEATURE_STEM=<stem>[,stem2...]  (module features.platform_steps.<platform>.<stem>_steps;
                                   default: weather)
                                   Use ``*`` / ``all`` to load every ``*_steps.py``
                                   in that platform directory.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path

from behave.step_registry import AmbiguousStep


def resolve_steps_platform() -> str:
    mode = (os.environ.get("EXPECTATIONS_MODE") or "verify").strip().lower()
    if mode == "capture":
        return (os.environ.get("SOURCE_PLATFORM") or "android").strip().lower()
    return (os.environ.get("TARGET_PLATFORM") or "harmonyos").strip().lower()


def _sanitize_stem(stem: str) -> str:
    return "".join(c if c.isalnum() or c == "_" else "_" for c in stem) or "weather"


def resolve_feature_stems() -> list[str]:
    raw = (os.environ.get("FEATURE_STEM") or "weather").strip()
    if raw.lower() in ("*", "all"):
        return ["*"]
    stems = [_sanitize_stem(part.strip()) for part in raw.split(",") if part.strip()]
    return stems or ["weather"]


def _platform_steps_dir(platform: str) -> Path:
    # this file: features/steps/load_platform_steps.py
    return Path(__file__).resolve().parents[1] / "platform_steps" / platform


def _module_names(platform: str, stems: list[str]) -> list[str]:
    if stems == ["*"]:
        steps_dir = _platform_steps_dir(platform)
        if not steps_dir.is_dir():
            return []
        names = []
        for path in sorted(steps_dir.glob("*_steps.py")):
            if path.name.startswith("_"):
                continue
            names.append(f"features.platform_steps.{platform}.{path.stem}")
        return names
    return [f"features.platform_steps.{platform}.{stem}_steps" for stem in stems]


_platform = resolve_steps_platform()
_stems = resolve_feature_stems()
_mod_names = _module_names(_platform, _stems)

if not _mod_names:
    raise ImportError(
        f"[expectations] no step modules for platform '{_platform}' "
        f"(FEATURE_STEM={os.environ.get('FEATURE_STEM')!r})."
    )

_loaded: list[str] = []
_errors: list[str] = []
for _mod_name in _mod_names:
    try:
        importlib.import_module(_mod_name)
        _loaded.append(_mod_name)
        print(f"[expectations] loaded steps: {_mod_name}")
    except AmbiguousStep as exc:
        # Same step text in a later file — keep the first definition.
        print(f"[expectations] duplicate step in {_mod_name} (kept earlier): {exc}")
        _loaded.append(_mod_name)
    except Exception as exc:  # noqa: BLE001 - surface clear load errors to behave startup
        _errors.append(f"{_mod_name}: {exc}")

if _errors and _stems != ["*"]:
    raise ImportError(
        f"[expectations] failed to load steps for platform '{_platform}' "
        f"(FEATURE_STEM={os.environ.get('FEATURE_STEM')!r} "
        f"EXPECTATIONS_MODE={os.environ.get('EXPECTATIONS_MODE')!r} "
        f"SOURCE_PLATFORM={os.environ.get('SOURCE_PLATFORM')!r} "
        f"TARGET_PLATFORM={os.environ.get('TARGET_PLATFORM')!r}). "
        f"Cause: {'; '.join(_errors)}"
    ) from None

if _errors:
    for msg in _errors:
        print(f"[expectations] skip steps module: {msg}")

if not _loaded:
    raise ImportError(
        f"[expectations] failed to load any steps for platform '{_platform}'. "
        f"Cause: {'; '.join(_errors) or 'no modules'}"
    )
