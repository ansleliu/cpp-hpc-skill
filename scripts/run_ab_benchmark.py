#!/usr/bin/env python3
"""Run randomized interleaved paired A/B trials.

All options must precede the command delimiters:
  run_ab_benchmark.py [options] --baseline ./old args --candidate ./new args
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import platform
import random
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Pattern

from run_benchmark import (
    PERFORMANCE_ENV_KEYS,
    command_identity,
    parse_env_overrides,
    percentile,
    run_once,
    speedup,
    summarize_values,
    validate_timing_options,
)


def split_commands(arguments: list[str]) -> tuple[list[str], list[str], list[str]]:
    try:
        baseline_index = arguments.index("--baseline")
        candidate_index = arguments.index("--candidate")
    except ValueError as exc:
        raise ValueError("both --baseline and --candidate command delimiters are required") from exc
    if candidate_index <= baseline_index:
        raise ValueError("--baseline must appear before --candidate")
    options = arguments[:baseline_index]
    baseline = arguments[baseline_index + 1 : candidate_index]
    candidate = arguments[candidate_index + 1 :]
    if not baseline or not candidate:
        raise ValueError("baseline and candidate commands must not be empty")
    return options, baseline, candidate


def metric_for(run: dict[str, Any], use_internal_metric: bool) -> float | None:
    if run["returncode"] != 0 or run["timed_out"]:
        return None
    value = run["metric_value"] if use_internal_metric else run["elapsed_seconds"]
    return float(value) if value is not None and math.isfinite(value) and value > 0 else None


def bootstrap_paired(ratios: list[float], samples: int, seed: int) -> dict[str, float] | None:
    if samples <= 0 or len(ratios) < 2:
        return None
    rng = random.Random(seed)
    estimates = [statistics.median(rng.choice(ratios) for _ in ratios) for _ in range(samples)]
    return {
        "lower_95": percentile(estimates, 0.025),
        "median": statistics.median(estimates),
        "upper_95": percentile(estimates, 0.975),
    }


def main(arguments: list[str] | None = None) -> int:
    raw_arguments = list(sys.argv[1:] if arguments is None else arguments)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warmup", type=int, default=1, help="Warm-up pairs before measurement.")
    parser.add_argument("--repeat", "-r", type=int, default=10, help="Measured A/B pairs.")
    parser.add_argument("--timeout", type=float, default=None, help="Timeout per command in seconds.")
    parser.add_argument("--delay", type=float, default=0.0, help="Delay between command runs in seconds.")
    parser.add_argument("--cwd", default=None)
    parser.add_argument("--env", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--metric-regex", default=None, help="Shared regex extracting comparable internal metrics.")
    parser.add_argument("--metric-source", choices=("stdout", "stderr", "both"), default="stdout")
    parser.add_argument("--metric-unit", default=None)
    parser.add_argument("--higher-is-better", action="store_true")
    parser.add_argument("--seed", type=int, default=20260813)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--allow-failure", action="store_true", help="Continue after failed or missing-metric runs.")
    parser.add_argument("--output-json", default="ab-benchmark-results.json")
    if raw_arguments in (["-h"], ["--help"]):
        parser.parse_args(raw_arguments)
    try:
        option_arguments, baseline_command, candidate_command = split_commands(raw_arguments)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    args = parser.parse_args(option_arguments)

    if args.warmup < 0 or args.repeat < 1 or args.bootstrap_samples < 0:
        parser.error("warmup/bootstrap must be >= 0 and repeat must be >= 1")
    try:
        validate_timing_options(args.timeout, args.delay)
        env_overrides = parse_env_overrides(args.env)
        metric_pattern: Pattern[str] | None = re.compile(args.metric_regex) if args.metric_regex else None
    except (ValueError, re.error) as exc:
        parser.error(str(exc))

    child_env = os.environ.copy()
    child_env.update(env_overrides)
    rng = random.Random(args.seed)
    runs: list[dict[str, Any]] = []
    fatal_status = 0
    total_runs = 2 * (args.warmup + args.repeat)

    def first_variants(count: int) -> list[str]:
        if count == 1:
            return [rng.choice(("baseline", "candidate"))]
        variants = ["baseline"] * ((count + 1) // 2) + ["candidate"] * (count // 2)
        rng.shuffle(variants)
        return variants

    def run_pair(pair_index: int, phase: str, first_variant: str) -> bool:
        nonlocal fatal_status
        second_variant = "candidate" if first_variant == "baseline" else "baseline"
        order = [first_variant, second_variant]
        commands = {"baseline": baseline_command, "candidate": candidate_command}
        for order_index, variant in enumerate(order, start=1):
            result = run_once(
                commands[variant],
                args.timeout,
                args.cwd,
                child_env,
                pair_index,
                phase,
                metric_pattern,
                args.metric_source,
            )
            result.update({"pair": pair_index, "variant": variant, "order_in_pair": order_index})
            runs.append(result)
            failed = result["returncode"] != 0 or result["timed_out"]
            invalid_metric = not failed and metric_for(result, metric_pattern is not None) is None
            if invalid_metric and result["metric_error"] is None:
                result["metric_error"] = "speedup samples must be finite and positive"
            if (failed or invalid_metric) and not args.allow_failure:
                fatal_status = (result["returncode"] or 124) if failed else 65
                return False
            if args.delay and len(runs) < total_runs:
                time.sleep(args.delay)
        return True

    for pair_index, first_variant in enumerate(first_variants(args.warmup), start=1):
        if not run_pair(pair_index, "warmup", first_variant):
            break
    if fatal_status == 0 or args.allow_failure:
        for pair_index, first_variant in enumerate(first_variants(args.repeat), start=1):
            if not run_pair(pair_index, "measure", first_variant):
                break

    use_internal_metric = metric_pattern is not None
    pairs: list[dict[str, Any]] = []
    measured_pair_ids = sorted({int(run["pair"]) for run in runs if run["phase"] == "measure"})
    for pair_index in measured_pair_ids:
        pair_runs = [run for run in runs if run["phase"] == "measure" and run["pair"] == pair_index]
        by_variant = {run["variant"]: run for run in pair_runs}
        if set(by_variant) != {"baseline", "candidate"}:
            continue
        baseline_value = metric_for(by_variant["baseline"], use_internal_metric)
        candidate_value = metric_for(by_variant["candidate"], use_internal_metric)
        if baseline_value is None or candidate_value is None:
            continue
        try:
            ratio = speedup(baseline_value, candidate_value, args.higher_is_better)
        except ValueError as exc:
            fatal_status = fatal_status or 65
            by_variant["candidate"]["metric_error"] = str(exc)
            continue
        pairs.append(
            {
                "pair": pair_index,
                "baseline": baseline_value,
                "candidate": candidate_value,
                "speedup": ratio,
                "first": min(pair_runs, key=lambda run: run["order_in_pair"])["variant"],
            }
        )

    baseline_values = [pair["baseline"] for pair in pairs]
    candidate_values = [pair["candidate"] for pair in pairs]
    ratios = [pair["speedup"] for pair in pairs]
    interval = bootstrap_paired(ratios, args.bootstrap_samples, args.seed + 1)
    warnings: list[str] = []
    if len(pairs) < 5:
        warnings.append("Fewer than five complete successful A/B pairs were collected.")
    if not use_internal_metric:
        warnings.append("Values include process startup and dynamic-loading time; use an internal metric or in-process harness for short kernels.")

    output = Path(args.output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "baseline_command": baseline_command,
        "candidate_command": candidate_command,
        "baseline_identity": command_identity(baseline_command, args.cwd, child_env),
        "candidate_identity": command_identity(candidate_command, args.cwd, child_env),
        "cwd": os.path.abspath(args.cwd or os.getcwd()),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "performance_environment": {key: child_env[key] for key in PERFORMANCE_ENV_KEYS if key in child_env},
        "environment_overrides": env_overrides,
        "warmup_pairs": args.warmup,
        "requested_pairs": args.repeat,
        "successful_pairs": len(pairs),
        "seed": args.seed,
        "metric": {
            "kind": "internal" if use_internal_metric else "process_wall_time",
            "regex": args.metric_regex,
            "source": args.metric_source if use_internal_metric else None,
            "unit": args.metric_unit if use_internal_metric else "seconds",
            "higher_is_better": args.higher_is_better,
        },
        "runs": runs,
        "pairs": pairs,
        "baseline_summary": summarize_values(baseline_values),
        "candidate_summary": summarize_values(candidate_values),
        "paired_speedup_summary": summarize_values(ratios),
        "paired_bootstrap_speedup_ci_95": interval,
        "bootstrap_samples": args.bootstrap_samples,
        "warnings": warnings,
    }
    for variant in ("baseline", "candidate"):
        if payload[f"{variant}_identity"].get("identity_error"):
            warnings.append(f"{variant} executable identity is unverified; see {variant}_identity.identity_error.")
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    print(f"Wrote JSON: {output}")
    print(f"Successful pairs: {len(pairs)} / {args.repeat}")
    if ratios:
        print(f"Median paired speedup: {statistics.median(ratios):.6g}x")
    if interval:
        print(f"Bootstrap 95% speedup interval: [{interval['lower_95']:.6g}, {interval['upper_95']:.6g}]")
    for warning in warnings:
        print("Warning:", warning)
    return int(fatal_status or (0 if pairs else 65))


if __name__ == "__main__":
    sys.exit(main())
