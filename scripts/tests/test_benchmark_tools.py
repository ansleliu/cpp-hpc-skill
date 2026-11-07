from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import compare_benchmarks  # noqa: E402
import run_ab_benchmark  # noqa: E402
import run_benchmark  # noqa: E402


def cli(script: str, arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script), *arguments],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


class BenchmarkToolTests(unittest.TestCase):
    def test_documented_python_help_entrypoints(self) -> None:
        for script in ("run_benchmark.py", "run_ab_benchmark.py", "compare_benchmarks.py", "collect_system_info.py"):
            with self.subTest(script=script):
                result = cli(script, ["--help"])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout)

    def test_summary_includes_tail_and_dispersion(self) -> None:
        summary = run_benchmark.summarize_values([1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertEqual(summary["median"], 3.0)
        self.assertGreater(summary["p95"], 4.0)
        self.assertEqual(summary["median_absolute_deviation"], 1.0)

    def test_run_once_extracts_last_named_metric(self) -> None:
        result = run_benchmark.run_once(
            [sys.executable, "-c", "print('metric=4'); print('metric=7.5')"],
            timeout=5.0,
            cwd=None,
            env=os.environ.copy(),
            index=1,
            phase="measure",
            metric_pattern=re.compile(r"metric=(?P<value>[0-9.]+)"),
            metric_source="stdout",
        )
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(result["metric_value"], 7.5)

    def test_independent_bootstrap_is_deterministic(self) -> None:
        first = compare_benchmarks.bootstrap_speedup([10, 11, 12], [8, 9, 10], False, 200, 123)
        second = compare_benchmarks.bootstrap_speedup([10, 11, 12], [8, 9, 10], False, 200, 123)
        self.assertEqual(first, second)
        self.assertIsNotNone(first)
        self.assertGreater(first["median"], 1.0)

    def test_command_identity_resolves_relative_to_child_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "app.bin"
            executable.write_bytes(b"current-artifact")
            identity = run_benchmark.command_identity(["./app.bin"], directory)
            self.assertTrue(Path(identity["resolved"]).samefile(executable))
            self.assertEqual(identity["size_bytes"], len(b"current-artifact"))

    def test_run_once_records_launch_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_benchmark.run_once(
                [str(Path(directory) / "missing-program")],
                5, None, os.environ.copy(), 1, "measure", None, "stdout",
            )
            self.assertEqual(result["returncode"], 127)
            self.assertFalse(result["timed_out"])
            self.assertIn("FileNotFoundError", result["launch_error"])
            self.assertIsNone(result["metric_value"])

    def test_command_lookup_respects_child_path_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            name = "child.exe" if os.name == "nt" else "child"
            target = Path(directory) / name
            shutil.copy2(sys.executable, target)
            env = {
                **os.environ,
                "PATH": directory + os.pathsep + os.environ.get("PATH", os.defpath),
                "PYTHONHOME": sys.prefix,
            }
            identity = run_benchmark.command_identity([name], None, env)
            result = run_benchmark.run_once(
                [name, "-c", "print('ok')"], 5, None, env, 1, "measure", None, "stdout",
            )
            self.assertTrue(Path(identity["resolved"]).samefile(target))
            self.assertEqual(result["returncode"], 0, result["stderr_tail"])
            self.assertIn("ok", result["stdout_tail"])

    def test_unexecutable_file_is_recorded_as_start_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "invalid.exe"
            target.write_bytes(b"not an executable")
            target.chmod(0o644)
            result = run_benchmark.run_once(
                [str(target)], 5, None, os.environ.copy(), 1, "measure", None, "stdout",
            )
        self.assertEqual(result["returncode"], 126)
        self.assertIsNotNone(result["launch_error"])
        self.assertFalse(result["timed_out"])

    def test_metric_extraction_rejects_nonfinite_values(self) -> None:
        for raw in ("nan", "inf", "1e999"):
            with self.subTest(raw=raw):
                value, error = run_benchmark.extract_metric(re.compile(r"metric=(\S+)"), "metric=" + raw)
                self.assertIsNone(value)
                self.assertIn("not finite", error)

    def test_optional_metric_capture_is_recorded_as_missing(self) -> None:
        result = run_benchmark.run_once(
            [sys.executable, "-c", "print('metric=')"], 5, None, os.environ.copy(),
            1, "measure", re.compile(r"metric=(?P<value>\d+)?"), "stdout",
        )
        self.assertEqual(result["returncode"], 0)
        self.assertIsNone(result["metric_value"])
        self.assertIsNotNone(result["metric_error"])

    def test_undecodable_output_does_not_discard_run(self) -> None:
        result = run_benchmark.run_once(
            [sys.executable, "-c", "import sys; sys.stdout.buffer.write(bytes([255])); print(' metric=7')"],
            5, None, os.environ.copy(), 1, "measure", re.compile(r"metric=(\d+)"), "stdout",
        )
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(result["metric_value"], 7)
        self.assertIn("\ufffd", result["stdout_tail"])

    @unittest.skipIf(os.name == "nt", "POSIX symlink-based virtual environment")
    def test_launch_preserves_virtual_environment_symlink(self) -> None:
        import venv

        with tempfile.TemporaryDirectory() as directory:
            environment = Path(directory) / "venv"
            venv.EnvBuilder(with_pip=False, symlinks=True).create(environment)
            executable = environment / "bin" / "python"
            self.assertTrue(executable.is_symlink())
            result = run_benchmark.run_once(
                [str(executable), "-c", "import sys; print(sys.prefix)"],
                5, None, os.environ.copy(), 1, "measure", None, "stdout",
            )
            self.assertEqual(result["returncode"], 0, result["stderr_tail"])
            self.assertEqual(Path(result["stdout_tail"].strip()), environment)

    def test_relative_executable_runs_from_child_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            name = "child.exe" if os.name == "nt" else "child"
            target = Path(directory) / name
            shutil.copy2(sys.executable, target)
            env = {**os.environ, "PYTHONHOME": sys.prefix}
            result = run_benchmark.run_once(
                ["./" + name, "-c", "print('metric=7')"],
                5, directory, env, 1, "measure", re.compile(r"metric=(\d+)"), "stdout",
            )
            self.assertEqual(result["returncode"], 0, result["stderr_tail"])
            self.assertEqual(result["metric_value"], 7)

    def test_relative_path_entries_use_child_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory) / "work"
            binaries = work / "bin"
            binaries.mkdir(parents=True)
            name = "path-probe.exe" if os.name == "nt" else "path-probe"
            target = binaries / name
            shutil.copy2(sys.executable, target)
            env = {
                **os.environ, "PATH": "bin" + os.pathsep + str(Path(sys.executable).parent),
                "PYTHONHOME": sys.prefix,
            }
            result = run_benchmark.run_once(
                [name, "-c", "print('from-child-path')"],
                5, str(work), env, 1, "measure", None, "stdout",
            )
            self.assertEqual(result["returncode"], 0, result["stderr_tail"])
            identity = run_benchmark.command_identity([name], str(work), env)
            self.assertTrue(Path(identity["resolved"]).samefile(target))

    @unittest.skipUnless(os.name == "nt", "Windows current-directory executable search")
    def test_child_path_is_not_shadowed_by_parent_current_directory(self) -> None:
        original = os.getcwd()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = root / "work"
            (work / "bin").mkdir(parents=True)
            parent_program = root / "path-probe.exe"
            child_program = work / "bin" / "path-probe.exe"
            shutil.copy2(sys.executable, parent_program)
            shutil.copy2(sys.executable, child_program)
            try:
                os.chdir(root)
                for name in ("path-probe.exe", "path-probe"):
                    with self.subTest(command=name):
                        resolved = run_benchmark.resolve_executable(name, str(work), {"PATH": "bin"})
                        self.assertTrue(Path(resolved).samefile(child_program))
            finally:
                os.chdir(original)

    @unittest.skipUnless(os.name == "nt", "Windows exclusive file sharing")
    def test_locked_executable_does_not_discard_cli_failure_records(self) -> None:
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        create = kernel.CreateFileW
        create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                           wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        create.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            locked = root / "locked.exe"
            locked.write_bytes(b"locked artifact")
            handle = create(str(locked), 0x80000000, 0, None, 3, 0x80, None)
            self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
            try:
                for script in ("run_benchmark.py", "run_ab_benchmark.py"):
                    with self.subTest(script=script):
                        output = root / (script + ".json")
                        arguments = ["--warmup", "0", "--repeat", "1", "--allow-failure",
                                     "--output-json", str(output)]
                        if script == "run_benchmark.py":
                            arguments += ["--", str(locked)]
                            identity_key = "command_identity"
                        else:
                            arguments += ["--bootstrap-samples", "0", "--baseline", str(locked),
                                          "--candidate", sys.executable, "-c", "pass"]
                            identity_key = "baseline_identity"
                        result = cli(script, arguments)
                        self.assertNotIn("Traceback", result.stderr)
                        self.assertTrue(output.is_file(), result.stderr)
                        data = json.loads(output.read_text(encoding="utf-8"))
                        self.assertTrue(data["runs"])
                        self.assertIn("PermissionError", data[identity_key]["identity_error"])
                        self.assertNotIn("sha256", data[identity_key])
            finally:
                kernel.CloseHandle(handle)

    def test_launch_failure_cli_preserves_json_and_allow_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for allowed in (False, True):
                with self.subTest(allow_failure=allowed):
                    output = Path(directory) / f"runs-{allowed}.json"
                    result = cli("run_benchmark.py", [
                        "--warmup", "0", "--repeat", "2",
                        "--output-json", str(output),
                        *(["--allow-failure"] if allowed else []),
                        "--", str(Path(directory) / "missing-program"),
                    ])
                    self.assertEqual(result.returncode, 0 if allowed else 127, result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    data = json.loads(output.read_text(encoding="utf-8"))
                    self.assertEqual(len(data["runs"]), 2 if allowed else 1)
                    self.assertEqual(data["elapsed_summary_seconds"]["count"], 0)

    def test_ab_rejects_zero_metrics_without_losing_raw_observation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for allowed in (False, True):
                with self.subTest(allow_failure=allowed):
                    output = Path(directory) / f"invalid-{allowed}.json"
                    result = cli("run_ab_benchmark.py", [
                        "--warmup", "0", "--repeat", "1", "--bootstrap-samples", "0",
                        "--metric-regex", r"metric=(\d+)", "--output-json", str(output),
                        *(["--allow-failure"] if allowed else []),
                        "--baseline", sys.executable, "-c", "print('metric=10')",
                        "--candidate", sys.executable, "-c", "print('metric=0')",
                    ])
                    self.assertEqual(result.returncode, 65, result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    data = json.loads(output.read_text(encoding="utf-8"))
                    self.assertEqual(data["successful_pairs"], 0)
                    self.assertTrue(any(run["metric_value"] == 0 for run in data["runs"]))

    def test_compare_rejects_invalid_samples_and_unit_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory) / "baseline.json"
            candidate = Path(directory) / "candidate.json"
            def save(path, values, unit):
                path.write_text(json.dumps({
                    "metric": {"unit": unit},
                    "runs": [{"phase": "measure", "returncode": 0,
                              "metric_value": value} for value in values],
                }), encoding="utf-8")

            save(baseline, [10, 11], "ms")
            for values, unit, message in (
                ([0, 8], "ms", "finite and positive"),
                ([-1, 8], "ms", "finite and positive"),
                ([float("nan"), 8], "ms", "finite and positive"),
                ([float("inf"), 8], "ms", "finite and positive"),
                ([8, 9], "seconds", "metric units differ"),
            ):
                with self.subTest(values=values, unit=unit):
                    save(candidate, values, unit)
                    result = cli("compare_benchmarks.py", [str(baseline), str(candidate)])
                    self.assertEqual(result.returncode, 2)
                    self.assertIn(message, result.stderr)
                    self.assertNotIn("Traceback", result.stderr)

    def test_compare_cli_exports_successful_measurements_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, value in (("baseline", 10), ("candidate", 8)):
                (root / f"{name}.csv").write_text(
                    "phase,returncode,timed_out,elapsed_seconds\n"
                    f"warmup,0,False,999\nmeasure,0,False,{value}\n"
                    f"measure,0,False,{value}\nmeasure,1,False,0\nmeasure,0,True,0\n",
                    encoding="utf-8",
                )
            output = root / "comparison.json"
            result = cli("compare_benchmarks.py", [
                str(root / "baseline.csv"), str(root / "candidate.csv"),
                "--bootstrap-samples", "100", "--output-json", str(output),
            ])
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["median_speedup"], 1.25)
            self.assertEqual(data["baseline"]["count"], 2)
            self.assertEqual(data["candidate"]["count"], 2)

    def test_auto_comparison_does_not_hide_missing_internal_metric(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for baseline_metric in (10, None):
                with self.subTest(baseline_metric=baseline_metric):
                    for name, value in (("baseline", baseline_metric), ("candidate", None)):
                        (root / f"{name}.json").write_text(json.dumps({
                            "metric": {"regex": "metric=(\\d+)", "unit": "ms"},
                            "runs": [{"phase": "measure", "returncode": 0, "timed_out": False,
                                      "metric_value": value, "elapsed_seconds": 1}],
                        }), encoding="utf-8")
                    arguments = [str(root / "baseline.json"), str(root / "candidate.json"),
                                 "--bootstrap-samples", "0"]
                    result = cli("compare_benchmarks.py", arguments)
                    self.assertEqual(result.returncode, 2, result.stdout)
                    self.assertIn("internal metric", result.stderr)
                    explicit = cli("compare_benchmarks.py", arguments + ["--field", "elapsed_seconds"])
                    self.assertEqual(explicit.returncode, 0, explicit.stderr)

    def test_runners_reject_nonfinite_timing_options_before_execution(self) -> None:
        for script in ("run_benchmark.py", "run_ab_benchmark.py"):
            for option, value in (("--delay", "nan"), ("--delay", "inf"),
                                  ("--timeout", "0"), ("--timeout", "-1"),
                                  ("--timeout", "nan"), ("--timeout", "inf")):
                with self.subTest(script=script, option=option, value=value):
                    arguments = [option, value, "--warmup", "0", "--repeat", "1"]
                    marker = [sys.executable, "-c", "print('SHOULD_NOT_RUN')"]
                    if script == "run_benchmark.py":
                        arguments += ["--", *marker]
                    else:
                        arguments += ["--baseline", *marker, "--candidate", *marker]
                    # main must reject before creating its default output.
                    with tempfile.TemporaryDirectory() as directory:
                        result = subprocess.run(
                            [sys.executable, str(SCRIPTS_DIR / script), *arguments], cwd=directory,
                            capture_output=True, text=True, timeout=10,
                        )
                        self.assertEqual(result.returncode, 2, result.stderr)
                        self.assertNotIn("Traceback", result.stderr)
                        self.assertNotIn("SHOULD_NOT_RUN", result.stdout)
                        self.assertFalse(list(Path(directory).iterdir()))

    def test_ab_delay_is_between_runs_only(self) -> None:
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(run_ab_benchmark.time, "sleep") as sleep:
                status = run_ab_benchmark.main([
                    "--warmup", "1", "--repeat", "1", "--delay", "0.1",
                    "--bootstrap-samples", "0", "--output-json", str(Path(directory) / "ab.json"),
                    "--baseline", sys.executable, "-c", "pass",
                    "--candidate", sys.executable, "-c", "pass",
                ])
            self.assertEqual(status, 0)
            self.assertEqual(sleep.call_count, 3)

    def test_interleaved_ab_uses_complete_pairs_and_internal_metric(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "ab.json"
            status = run_ab_benchmark.main(
                [
                    "--warmup",
                    "0",
                    "--repeat",
                    "4",
                    "--bootstrap-samples",
                    "200",
                    "--seed",
                    "42",
                    "--metric-regex",
                    r"metric=(?P<value>[0-9.]+)",
                    "--output-json",
                    str(output),
                    "--baseline",
                    sys.executable,
                    "-c",
                    "print('metric=10')",
                    "--candidate",
                    sys.executable,
                    "-c",
                    "print('metric=8')",
                ]
            )
            self.assertEqual(status, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["successful_pairs"], 4)
            self.assertEqual(payload["paired_speedup_summary"]["median"], 1.25)
            self.assertEqual({pair["first"] for pair in payload["pairs"]}, {"baseline", "candidate"})


if __name__ == "__main__":
    unittest.main()
