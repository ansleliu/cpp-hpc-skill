#!/usr/bin/env python3
"""Run a command repeatedly and preserve reproducibility metadata."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Pattern


PERFORMANCE_ENV_KEYS = (
    "OMP_NUM_THREADS",
    "OMP_PROC_BIND",
    "OMP_PLACES",
    "OMP_SCHEDULE",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "BLIS_NUM_THREADS",
    "TBB_NUM_THREADS",
    "CUDA_VISIBLE_DEVICES",
    "HIP_VISIBLE_DEVICES",
    "ROCR_VISIBLE_DEVICES",
    "SYCL_DEVICE_FILTER",
)


def tail(text: str, limit: int = 4000) -> str:
    return text if len(text) <= limit else text[-limit:]


def as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode(errors="replace") if isinstance(value, bytes) else value


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def summarize_values(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0}
    mean = statistics.mean(values)
    median = statistics.median(values)
    result: dict[str, Any] = {
        "count": len(values),
        "median": median,
        "mean": mean,
        "min": min(values),
        "max": max(values),
        "p90": percentile(values, 0.90),
        "p95": percentile(values, 0.95),
        "p99": percentile(values, 0.99),
        "median_absolute_deviation": statistics.median(abs(value - median) for value in values),
    }
    if len(values) >= 2:
        stdev = statistics.stdev(values)
        result["stdev"] = stdev
        result["coefficient_of_variation"] = stdev / mean if mean else None
    else:
        result["stdev"] = None
        result["coefficient_of_variation"] = None
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_executable(executable: str, cwd: str | None, env: dict[str, str] | None = None) -> str | None:
    candidate = Path(executable)
    base = Path(cwd or os.getcwd()).absolute()
    has_path_component = candidate.parent != Path(".") or executable.startswith(".")
    if candidate.is_absolute() or has_path_component:
        return str((base / candidate).absolute())
    search_path = (env if env is not None else os.environ).get("PATH", os.defpath)
    # A directory-qualified lookup avoids Windows implicitly searching the parent's cwd.
    for entry in search_path.split(os.pathsep):
        resolved = shutil.which(str((base / entry / candidate).absolute()))
        if resolved:
            return str(Path(resolved).absolute())
    return None


def command_identity(command: list[str], cwd: str | None, env: dict[str, str] | None = None) -> dict[str, Any]:
    identity: dict[str, Any] = {"requested": command[0], "resolved": None}
    try:
        resolved = resolve_executable(command[0], cwd, env)
        identity["resolved"] = resolved
        if resolved and Path(resolved).is_file():
            path = Path(resolved)
            identity.update({"size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    except OSError as exc:
        identity["identity_error"] = f"{type(exc).__name__}: {exc}"
    return identity


def validate_speedup_values(values: list[float]) -> None:
    if not values or any(not math.isfinite(value) or value <= 0 for value in values):
        raise ValueError("speedup samples must be finite and positive")


def speedup(baseline: float, candidate: float, higher_is_better: bool) -> float:
    validate_speedup_values([baseline, candidate])
    numerator, denominator = (candidate, baseline) if higher_is_better else (baseline, candidate)
    ratio = numerator / denominator
    validate_speedup_values([ratio])
    return ratio


def validate_timing_options(timeout: float | None, delay: float) -> None:
    if not math.isfinite(delay) or delay < 0:
        raise ValueError("--delay must be finite and >= 0")
    if timeout is not None and (not math.isfinite(timeout) or timeout <= 0):
        raise ValueError("--timeout must be finite and > 0")


def parse_env_overrides(values: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"invalid --env value {value!r}; expected KEY=VALUE")
        key, item = value.split("=", 1)
        if not key:
            raise ValueError("environment key must not be empty")
        overrides[key] = item
    return overrides


def metric_text(stdout: str, stderr: str, source: str) -> str:
    if source == "stdout":
        return stdout
    if source == "stderr":
        return stderr
    return stdout + "\n" + stderr


def extract_metric(pattern: Pattern[str] | None, text: str) -> tuple[float | None, str | None]:
    if pattern is None:
        return None, None
    matches = list(pattern.finditer(text))
    if not matches:
        return None, "metric regex did not match"
    match = matches[-1]
    if "value" in match.groupdict():
        raw = match.group("value")
    elif match.lastindex:
        raw = match.group(1)
    else:
        raw = match.group(0)
    if raw is None:
        return None, "metric capture group did not participate in the match"
    try:
        value = float(raw.replace(",", ""))
        if not math.isfinite(value):
            return None, f"metric value is not finite: {raw!r}"
        return value, None
    except ValueError:
        return None, f"metric value is not numeric: {raw!r}"


def run_once(
    command: list[str],
    timeout: float | None,
    cwd: str | None,
    env: dict[str, str],
    index: int,
    phase: str,
    metric_pattern: Pattern[str] | None,
    metric_source: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    started_wall = dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        executable = resolve_executable(command[0], cwd, env)
        if executable is None:
            raise FileNotFoundError(f"executable not found in child PATH: {command[0]}")
        proc = subprocess.run(
            [executable, *command[1:]],
            cwd=cwd,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        elapsed = time.perf_counter() - started
        metric, metric_error = extract_metric(
            metric_pattern,
            metric_text(proc.stdout, proc.stderr, metric_source),
        )
        return {
            "phase": phase,
            "index": index,
            "started_at": started_wall,
            "elapsed_seconds": elapsed,
            "metric_value": metric,
            "metric_error": metric_error,
            "launch_error": None,
            "returncode": proc.returncode,
            "timed_out": False,
            "stdout_tail": tail(proc.stdout),
            "stderr_tail": tail(proc.stderr),
        }
    except (subprocess.TimeoutExpired, OSError) as exc:
        elapsed = time.perf_counter() - started
        timed_out = isinstance(exc, subprocess.TimeoutExpired)
        launch_error = None if timed_out else f"{type(exc).__name__}: {exc}"
        return {
            "phase": phase,
            "index": index,
            "started_at": started_wall,
            "elapsed_seconds": elapsed,
            "metric_value": None,
            "metric_error": "command timed out" if timed_out else "command could not be started",
            "launch_error": launch_error,
            "returncode": None if timed_out else (127 if isinstance(exc, FileNotFoundError) else 126),
            "timed_out": timed_out,
            "stdout_tail": tail(as_text(exc.stdout)) if timed_out else "",
            "stderr_tail": tail(as_text(exc.stderr)) if timed_out else launch_error,
        }


def write_csv(path: Path, runs: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        fieldnames = [
            "phase",
            "index",
            "elapsed_seconds",
            "metric_value",
            "metric_error",
            "launch_error",
            "returncode",
            "timed_out",
            "started_at",
        ]
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for run in runs:
            writer.writerow({key: run.get(key) for key in fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warmup", type=int, default=1, help="Warm-up runs before measurement.")
    parser.add_argument("--repeat", "-r", type=int, default=10, help="Measured repetitions.")
    parser.add_argument("--timeout", type=float, default=None, help="Timeout per run in seconds.")
    parser.add_argument("--delay", type=float, default=0.0, help="Delay between runs in seconds.")
    parser.add_argument("--cwd", default=None, help="Working directory for the command.")
    parser.add_argument("--env", action="append", default=[], metavar="KEY=VALUE", help="Child environment override.")
    parser.add_argument("--metric-regex", default=None, help="Regex extracting an internal metric; use group 'value' or the first group.")
    parser.add_argument("--metric-source", choices=("stdout", "stderr", "both"), default="stdout")
    parser.add_argument("--metric-unit", default=None, help="Unit for the extracted internal metric.")
    parser.add_argument("--output-json", default="benchmark-results.json", help="JSON output path.")
    parser.add_argument("--output-csv", default=None, help="Optional CSV output path.")
    parser.add_argument("--allow-failure", action="store_true", help="Keep running after failures or missing metrics.")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to run, usually after --.")
    args = parser.parse_args()

    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("missing command; use: run_benchmark.py [options] -- ./app args")
    if args.warmup < 0 or args.repeat < 1:
        parser.error("--warmup must be >= 0; --repeat must be >= 1")

    try:
        validate_timing_options(args.timeout, args.delay)
        env_overrides = parse_env_overrides(args.env)
        metric_pattern = re.compile(args.metric_regex) if args.metric_regex else None
    except (ValueError, re.error) as exc:
        parser.error(str(exc))

    child_env = os.environ.copy()
    child_env.update(env_overrides)
    runs: list[dict[str, Any]] = []
    exit_code = 0

    def execute_phase(phase: str, count: int) -> bool:
        nonlocal exit_code
        for index in range(1, count + 1):
            result = run_once(
                command,
                args.timeout,
                args.cwd,
                child_env,
                index,
                phase,
                metric_pattern,
                args.metric_source,
            )
            runs.append(result)
            failed = result["returncode"] != 0 or result["timed_out"]
            missing_metric = metric_pattern is not None and result["metric_value"] is None
            if (failed or missing_metric) and not args.allow_failure:
                exit_code = (result["returncode"] or 124) if failed else 65
                return False
            if args.delay and (index != count or phase == "warmup"):
                time.sleep(args.delay)
        return True

    if execute_phase("warmup", args.warmup):
        execute_phase("measure", args.repeat)

    measured = [run for run in runs if run["phase"] == "measure" and run["returncode"] == 0 and not run["timed_out"]]
    elapsed_values = [float(run["elapsed_seconds"]) for run in measured]
    metric_values = [float(run["metric_value"]) for run in measured if run["metric_value"] is not None]
    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 2,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "command": command,
        "command_identity": command_identity(command, args.cwd, child_env),
        "cwd": os.path.abspath(args.cwd or os.getcwd()),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "performance_environment": {key: child_env[key] for key in PERFORMANCE_ENV_KEYS if key in child_env},
        "environment_overrides": env_overrides,
        "warmup": args.warmup,
        "repeat": args.repeat,
        "timeout_seconds": args.timeout,
        "delay_seconds": args.delay,
        "metric": {
            "regex": args.metric_regex,
            "source": args.metric_source if args.metric_regex else None,
            "unit": args.metric_unit,
        },
        "runs": runs,
        "elapsed_summary_seconds": summarize_values(elapsed_values),
        "metric_summary": summarize_values(metric_values) if metric_pattern else None,
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    if args.output_csv:
        write_csv(Path(args.output_csv), runs)

    print(f"Wrote JSON: {output_path}")
    if payload["command_identity"].get("identity_error"):
        print("Warning: executable identity is unverified; see command_identity.identity_error.")
    if args.output_csv:
        print(f"Wrote CSV: {args.output_csv}")
    elapsed_summary = payload["elapsed_summary_seconds"]
    print(f"Measured successful runs: {elapsed_summary['count']}")
    if elapsed_summary["count"]:
        print(f"Process median seconds: {elapsed_summary['median']:.9g}")
        print(f"Process P95/P99 seconds: {elapsed_summary['p95']:.9g} / {elapsed_summary['p99']:.9g}")
    if metric_pattern and payload["metric_summary"] and payload["metric_summary"]["count"]:
        metric_summary = payload["metric_summary"]
        unit = f" {args.metric_unit}" if args.metric_unit else ""
        print(f"Internal metric median: {metric_summary['median']:.9g}{unit}")

    return int(exit_code)


if __name__ == "__main__":
    sys.exit(main())
