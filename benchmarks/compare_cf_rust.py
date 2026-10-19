#!/usr/bin/env python3
"""Reproducible TLHdig TF 13.1.0 vs Context-Fabric 0.6.0rc1 benchmark.

Each invocation is a fresh process. Run twice per engine (cold and warm).
All data are read from a fixed release snapshot, never inferred from a synthetic dataset.
"""
import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import resource
import sys
import time
import traceback

import psutil


def mem():
    p = psutil.Process()
    x = p.memory_full_info()
    return {
        "rss_mib": round(x.rss / 1048576, 2),
        "uss_mib": round(getattr(x, "uss", 0) / 1048576, 2),
        "pss_mib": round(getattr(x, "pss", 0) / 1048576, 2),
        "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2),
    }


def digest(data):
    serialized = json.dumps(data, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def timed(actions, label, f):
    start = time.perf_counter()
    try:
        value = f()
        actions[label] = {"seconds": round(time.perf_counter() - start, 6)}
        return value
    except BaseException as e:
        actions[label] = {
            "seconds": round(time.perf_counter() - start, 6),
            "error": type(e).__name__ + ": " + str(e),
        }
        traceback.print_exc()
        return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("engine", choices=("tf", "cf"))
    p.add_argument("phase", choices=("first", "repeat"))
    p.add_argument("dataset", type=Path)
    p.add_argument("--all", action="store_true", help="Load all features instead of the focused workload.")
    a = p.parse_args()

    result = {
        "engine": a.engine,
        "phase": a.phase,
        "dataset": str(a.dataset),
        "scope": "all" if a.all else "focused",
        "python": platform.python_version(),
        "system": platform.platform(),
        "memory_before": mem(),
        "ops": {},
        "checks": {},
    }
    package = "text-fabric" if a.engine == "tf" else "context-fabric"
    result["version"] = metadata.version(package)
    if a.engine == "tf":
        from tf.fabric import Fabric
    else:
        from cfabric import Fabric

    start = time.perf_counter()
    try:
        engine = Fabric(locations=str(a.dataset))
        if a.all:
            api = engine.loadAll()
        else:
            api = engine.load("sym after trans lemma gloss morph pos cu_sign cu_aligned selected", silent="deep")
        if api is None:
            raise RuntimeError("engine returned no API")
        result["load_seconds"] = round(time.perf_counter() - start, 6)
        result["memory_after_load"] = mem()

        F, L, T, S, E = api.F, api.L, api.T, api.S, api.E
        actions = result["ops"]

        words = timed(actions, "enumerate_all_words", lambda: F.otype.s("word"))
        signs = timed(actions, "enumerate_all_signs", lambda: F.otype.s("sign"))
        docs = timed(actions, "enumerate_all_documents", lambda: F.otype.s("document"))
        result["counts"] = {
            "word": len(words) if words is not None else -1,
            "sign": len(signs) if signs is not None else -1,
            "document": len(docs) if docs is not None else -1,
        }
        if words and signs:
            word_sample = words[:1000]
            sign_sample = signs[:1000]
            result["checks"]["word_trans_first_1000"] = digest([(w, F.trans.v(w)) for w in word_sample])
            result["checks"]["sign_sym_first_1000"] = digest([(s, F.sym.v(s)) for s in sign_sample])

            fv = F.trans.v
            sv = F.sym.v
            timed(actions, "feature_trans_100k", lambda: sum(bool(fv(w)) for w in words[:100000]))
            timed(actions, "feature_sym_100k", lambda: sum(bool(sv(s)) for s in signs[:100000]))

            wd = timed(actions, "locality_word_to_sign_10k", lambda: [
                (w, tuple(L.d(w, otype="sign"))) for w in words[:10000]
            ])
            if wd is not None:
                result["checks"]["word_to_sign_first_10k"] = digest(wd)

            su = timed(actions, "locality_sign_to_word_10k", lambda: [
                (s, tuple(L.u(s, otype="word"))) for s in signs[:10000]
            ])
            if su is not None:
                result["checks"]["sign_to_word_first_10k"] = digest(su)

            sections = timed(actions, "section_from_word_1k", lambda: [
                T.sectionFromNode(w) for w in words[:1000]
            ])
            if sections is not None:
                result["checks"]["sections_first_1k"] = digest(sections)

            selections = timed(actions, "selected_analyses_10k", lambda: [
                (w, tuple(E.selected.f(w))) for w in words[:10000]
            ])
            if selections is not None:
                result["checks"]["selected_first_10k"] = digest(selections)

            results = timed(actions, "search_word_limit_20", lambda: tuple(
                S.search("word", limit=20, silent="deep")
            ))
            if results is not None:
                result["checks"]["search_word_limit_20"] = digest(results)

        result["memory_after_workload"] = mem()
        result["failed_operations"] = [k for k,v in actions.items() if "error" in v]
    except BaseException as e:
        result["fatal_error"] = type(e).__name__ + ": " + str(e)
        result["load_or_failure_seconds"] = round(time.perf_counter() - start, 6)
        result["memory_at_failure"] = mem()
        traceback.print_exc()
    finally:
        print("BENCH_JSON:" + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
        Path(os.environ.get("BENCH_OUT", ".")).mkdir(parents=True, exist_ok=True)
        filename = f"{a.engine}_{a.phase}_{'all' if a.all else 'focused'}.json"
        (Path(os.environ.get("BENCH_OUT", ".")) / filename).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 1 if result.get("fatal_error") or result.get("failed_operations") else 0


if __name__ == "__main__":
    sys.exit(main())
