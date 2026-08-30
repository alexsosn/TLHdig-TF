#!/usr/bin/env python
"""Gate: does app/config.yaml describe the dataset that actually shipped?

Runs in under a second, against the files, rather than waiting for `use()` to load 5 GB
and then failing -- or worse, not failing, because a mis-typed `features:` entry renders
as nothing instead of raising.
"""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import TF_VERSION, appcheck
from tlhdig.paths import ROOT


def main() -> int:
    tf_dir = ROOT / "tf" / TF_VERSION
    config_path = ROOT / "app" / "config.yaml"
    if not config_path.is_file():
        print(f"no app config at {config_path}; nothing to check")
        return 0
    if not (tf_dir / "otype.tf").is_file():
        print(f"no dataset at {tf_dir}; build it first")
        return 1

    config = yaml.safe_load(config_path.read_text(encoding="utf8")) or {}
    problems = appcheck.check(tf_dir, config)
    types = len(config.get("typeDisplay") or {})
    if problems:
        print(f"APP CONFIG FAILED: {len(problems)} problem(s)")
        for p in problems:
            print("  " + p)
        return 1
    print(f"app/config.yaml matches tf/{TF_VERSION}: {types} node types, every named feature present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
