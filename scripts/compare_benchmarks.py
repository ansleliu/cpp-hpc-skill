#!/usr/bin/env python3
"""Compare saved benchmark samples and estimate uncertainty by bootstrap."""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import sys
from pathlib import Path
from typing import Any

from run_benchmark import percentile, speedup, summarize_values, validate_speedup_values


def successful_json_runs(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        run
        for run in data.get("runs", [])
        if run.get("phase") == "measure" and run.get("returncode") == 0 and not run.get("timed_out")
    ]


def read_json_values(path: Path, field: str) -> list[float]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "runs" in data:
        return [float(run[field]) for run in successful_json_runs(data) if run.get(field) is not None]
    if field in data:
        return [float(data[field])]
    return []


def read_csv_values(path: Path, field: str) -> list[float]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if field not in (reader.fieldnames or []):
            return []
        return [
            float(row[field])
            for row in reader
            if row.get(field) not in {None, ""}
            and row.get("phase", "measure") == "measure"
            and row.get("timed_out", "False").lower() not in {"true", "1", "yes"}
            and row.get("returncode", "0") in {"0", "0.0", ""}
        ]


def read_values(path: Path, field: str) -> list[float]:
    return read_json_values(path, field) if path.suffix.lower() == ".json" else read_csv_values(path, field)


def json_metric(path: Path) -> dict[str, Any]:
    if path.suffix.lower() != ".json":
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    metric = data.get("metric")
    return metric if isinstance(metric, dict) else {}


def bootstrap_speedup(
    baseline: list[float],
    candidate: list[float],
    higher_is_better: bool,
    samples: int,
    seed: int,
) -> dict[str, float] | None:
    if samples <= 0 or len(baseline) < 2 or len(candidate) < 2:
        return None
    rng = random.Random(seed)
    estimates: list[float] = []
    for _ in range(samples):
        baseline_sample = [rng.choice(baseline) for _ in baseline]
        candidate_sample = [rng.choice(candidate) for _ in candidate]
        estimates.append(
            speedup(
                statistics.median(baseline_sample),
                statistics.median(candidate_sample),
                higher_is_better,
            )
        )
    return {
        "lower_95": percentile(estimates, 0.025),
        "median": statistics.median(estimates),
        "upper_95": percentile(estimates, 0.975),
    }


def select_field(baseline_path: Path, candidate_path: Path, requested: str) -> tuple[str, list[float], list[float]]:
    if requested != "auto":
        return requested, read_values(baseline_path, requested), read_values(candidate_path, requested)
    baseline_metric = read_values(baseline_path, "metric_value")
    candidate_metric = read_values(candidate_path, "metric_value")
    configured = json_metric(baseline_path).get("regex") or json_metric(candidate_path).get("regex")
    if baseline_metric or candidate_metric or configured:
        if not baseline_metric or not candidate_metric:
            raise ValueError("internal metric samples missing; use --field elapsed_seconds explicitly for process timing")
        return "metric_value", baseline_metric, candidate_metric
    return "elapsed_seconds", read_values(baseline_path, "elapsed_seconds"), read_values(candidate_path, "elapsed_seconds")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--field", choices=("auto", "elapsed_seconds", "metric_value"), default="auto")
    parser.add_argument("--higher-is-better", action="store_true", help="Treat larger values as better.")
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260813)
    parser.add_argument("--output-json", default=None)
    args = parser.parse_args()

    if args.bootstrap_samples < 0:
        parser.error("--bootstrap-samples must be >= 0")

    field, baseline_values, candidate_values = select_field(args.baseline, args.candidate, args.field)
    validate_speedup_values(baseline_values)
    validate_speedup_values(candidate_values)
    unit = "seconds" if field == "elapsed_seconds" else None
    if field == "metric_value":
        baseline_unit = json_metric(args.baseline).get("unit")
        candidate_unit = json_metric(args.candidate).get("unit")
        if baseline_unit and candidate_unit and baseline_unit != candidate_unit:
            raise ValueError(f"metric units differ: {baseline_unit!r} vs {candidate_unit!r}")
        unit = baseline_unit or candidate_unit
    baseline = summarize_values(baseline_values)
    candidate = summarize_values(candidate_values)
    median_speedup = speedup(baseline["median"], candidate["median"], args.higher_is_better)
    percent_change = (candidate["median"] - baseline["median"]) / baseline["median"] * 100.0
    interval = bootstrap_speedup(
        baseline_values,
        candidate_values,
        args.higher_is_better,
        args.bootstrap_samples,
        args.seed,
    )
    warnings = [
        "This is an independent-sample comparison. Prefer randomized interleaved paired A/B trials when machine drift is material.",
        "A bootstrap interval estimates sampling uncertainty; it does not prove improvement for untested workloads or environments.",
    ]
    if min(len(baseline_values), len(candidate_values)) < 5:
        warnings.append("Fewer than five successful values were available in at least one sample.")

    result = {
        "schema_version": 2,
        "baseline_file": str(args.baseline),
        "candidate_file": str(args.candidate),
        "field": field,
        "unit": unit,
        "higher_is_better": args.higher_is_better,
        "baseline": baseline,
        "candidate": candidate,
        "median_speedup": median_speedup,
        "candidate_median_percent_change": percent_change,
        "bootstrap_speedup_ci_95": interval,
        "bootstrap_samples": args.bootstrap_samples,
        "seed": args.seed,
        "warnings": warnings,
    }

    if args.output_json:
        output = Path(args.output_json)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        print(f"Wrote JSON: {output}")

    print(f"Field: {field}")
    print("Baseline median:", f"{baseline['median']:.9g}", f"(n={baseline['count']})")
    print("Candidate median:", f"{candidate['median']:.9g}", f"(n={candidate['count']})")
    print("Median speedup:", f"{median_speedup:.6g}x")
    print("Candidate median percent change:", f"{percent_change:.4g}%")
    if interval:
        print(
            "Bootstrap 95% speedup interval:",
            f"[{interval['lower_95']:.6g}, {interval['upper_95']:.6g}]",
        )
    for warning in warnings:
        print("Warning:", warning)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
