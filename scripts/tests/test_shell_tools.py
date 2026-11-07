"""Exercise shell entrypoints through Bash without requiring HPC compilers."""

import os
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
GIT_BASH = Path("C:/Program Files/Git/bin/bash.exe")
BASH = str(GIT_BASH) if os.name == "nt" and GIT_BASH.is_file() else shutil.which("bash")

PERF_STUB = '''perf() {
  local output=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -o) output="$2"; shift 2 ;;
      --) shift; break ;;
      *) shift ;;
    esac
  done
  printf 'controlled-test-counter\\n' > "$output" || return 74
  "$@"
}; export -f perf'''


@unittest.skipUnless(BASH, "Bash is unavailable")
class ShellToolTests(unittest.TestCase):
    def invoke(self, script, arguments, directory, setup=""):
        return subprocess.run(
            [BASH, "-c", setup + '\nexec bash "$@"', "shell-test",
             (SCRIPTS / script).as_posix(), *map(str, arguments)],
            cwd=directory, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
        )

    def test_report_write_failures_do_not_run_compiler(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "report"
            (output / "command.txt").mkdir(parents=True)
            marker = root / "executed"
            result = self.invoke("check_vectorization.sh", [
                "--compiler", "gcc", "--output-dir", output, "--", BASH,
                "-c", 'touch "$1"', "compiler-stub", marker.as_posix(),
            ], directory)
            self.assertEqual(result.returncode, 74, result.stderr)
            self.assertFalse(marker.exists())

    def test_vectorization_preserves_command_status_and_detects_summary_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for code in (0, 42):
                for broken in (False, True):
                    with self.subTest(code=code, broken_summary=broken):
                        output = root / f"{code}-{broken}"
                        output.mkdir()
                        if broken:
                            (output / "summary.txt").mkdir()
                        result = self.invoke("check_vectorization.sh", [
                            "--compiler", "gcc", "--output-dir", output, "--", BASH,
                            "-c", f"echo compiler-output; exit {code}", "compiler-stub",
                        ], directory)
                        self.assertEqual(result.returncode, code or (74 if broken else 0), result.stderr)
                        if not broken:
                            summary = (output / "summary.txt").read_text(encoding="utf-8")
                            self.assertIn(f"exit_status={code}", summary)
                            self.assertIn("compiler-stub", summary)
                            self.assertIn("compiler-output", (output / "compiler-output.txt").read_text())

    def test_fallback_collector_propagates_output_failure(self):
        setup = 'python3() { return 49; }; python() { return 49; }; export -f python3 python'
        with tempfile.TemporaryDirectory() as directory:
            blocker = Path(directory) / "blocker"
            blocker.touch()
            result = self.invoke("collect_system_info.sh", [
                "--json", blocker.as_posix() + "/out.json", "--text", blocker.as_posix() + "/out.txt",
            ], directory, setup)
            self.assertEqual(result.returncode, 74, result.stderr)
            self.assertNotIn("Wrote fallback", result.stdout)

    def test_fallback_collector_propagates_write_time_failure(self):
        if subprocess.run([BASH, "-c", "test -c /dev/full"], check=False).returncode:
            self.skipTest("/dev/full is unavailable")
        setup = '''python3() { return 49; }; python() { return 49; }
uname() { :; }; lscpu() { :; }; free() { :; }
export -f python3 python uname lscpu free'''
        with tempfile.TemporaryDirectory() as directory:
            result = self.invoke("collect_system_info.sh", [
                "--json", Path(directory) / "out.json", "--text", "/dev/full",
            ], directory, setup)
            self.assertEqual(result.returncode, 74, result.stderr)
            self.assertNotIn("Wrote fallback", result.stdout)

    @unittest.skipIf(os.name == "nt", "POSIX filenames containing quotes and control characters")
    def test_fallback_collector_escapes_json_path(self):
        setup = 'python3() { return 49; }; python() { return 49; }; export -f python3 python'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            text = root / '\u4e2d\u6587quote"back\\line\ncontrol\x01.txt'
            output = root / "out.json"
            result = self.invoke("collect_system_info.sh", ["--json", output, "--text", text], directory, setup)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["text_file"], str(text))
            self.assertTrue(text.is_file())

    def test_perf_unavailable_does_not_report_success_or_run_target(self):
        setups = (
            'perf() { return 255; }; export -f perf',
            'command() { if [[ "$1" == "-v" && "$2" == "perf" ]]; then return 1; fi; builtin command "$@"; }; export -f command',
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, setup in enumerate(setups):
                with self.subTest(mode=index):
                    marker = root / f"ran-{index}"
                    result = self.invoke("perf_stat.sh", [
                        "--events", "cycles", "--output-dir", root / str(index), "--", BASH,
                        "-c", 'touch "$1"', "target", marker.as_posix(),
                    ], directory, setup)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(marker.exists())

    def test_perf_propagates_target_and_summary_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for code in (0, 42):
                for broken in (False, True):
                    with self.subTest(code=code, broken_summary=broken):
                        output = root / f"{code}-{broken}"
                        output.mkdir()
                        if broken:
                            (output / "summary.txt").mkdir()
                        result = self.invoke("perf_stat.sh", [
                            "--repeat", "1", "--events", "cycles", "--output-dir", output,
                            "--", BASH, "-c", f"exit {code}",
                        ], directory, PERF_STUB)
                        self.assertEqual(result.returncode, code or (74 if broken else 0), result.stderr)
                        if not broken:
                            self.assertIn(f"perf_exit_status={code}", (output / "summary.txt").read_text())

    def test_perf_diagnostic_open_failure_is_wrapper_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "report"
            (output / "perf-diagnostics.txt").mkdir(parents=True)
            marker = root / "executed"
            result = self.invoke("perf_stat.sh", [
                "--repeat", "1", "--events", "cycles", "--output-dir", output,
                "--", BASH, "-c", 'touch "$1"', "target", marker.as_posix(),
            ], directory, PERF_STUB)
            self.assertEqual(result.returncode, 74, result.stderr)
            self.assertFalse(marker.exists())

    def test_no_command_prints_all_compiler_flags_without_creating_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [BASH, str(SCRIPTS / "check_vectorization.sh")],
                cwd=directory, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            for flag in ("-fopt-info-vec", "-Rpass=loop-vectorize", "/clang:-Rpass", "-qopt-report", "/Qvec-report"):
                self.assertIn(flag, result.stdout)
            self.assertFalse(list(Path(directory).iterdir()))

    def test_auto_detection_handles_versioned_and_windows_compiler_names(self):
        with tempfile.TemporaryDirectory() as directory:
            for index, (name, kind) in enumerate((
                ("clang++-18", "clang"), ("clang++.exe", "clang"),
                ("clang-cl-18.exe", "clang-cl"), ("icpx.exe", "intel"),
                ("g++-14", "gcc"), ("aarch64-linux-gnu-g++-14", "gcc"),
            )):
                with self.subTest(compiler=name):
                    output = Path(directory) / str(index)
                    # Missing commands still expose dispatch and preserve exit status.
                    result = subprocess.run(
                        [BASH, str(SCRIPTS / "check_vectorization.sh"),
                         "--output-dir", str(output), "--", str(Path(directory) / name)],
                        capture_output=True, text=True, timeout=10,
                    )
                    self.assertEqual(result.returncode, 127)
                    self.assertIn(f"compiler_kind={kind}", result.stdout)

    def test_unknown_compiler_requires_explicit_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [BASH, str(SCRIPTS / "check_vectorization.sh"),
                 "--", str(Path(directory) / "unknown-compiler")],
                cwd=directory, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("--compiler", result.stderr)
            self.assertFalse(list(Path(directory).iterdir()))

    def test_collector_falls_back_from_unusable_python3(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bad = root / "python3"
            good = root / "python"
            bad.write_text("#!/usr/bin/env bash\nexit 49\n", encoding="utf-8")
            good.write_text(
                "#!/usr/bin/env bash\nif [[ \"$1\" == '-c' ]]; then exit 0; fi\nprintf '%s\\n' \"$@\"\n",
                encoding="utf-8",
            )
            bad.chmod(0o755)
            good.chmod(0o755)
            # Put the simulated Store alias before the usable interpreter.
            command = 'test_dir="$(cd "$1" && pwd)"; PATH="$test_dir:$PATH"; export PATH; exec bash "$2" --help'
            result = subprocess.run(
                [BASH, "-c", command, "collector-test", root.as_posix(),
                 (SCRIPTS / "collect_system_info.sh").as_posix()],
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("collect_system_info.py", result.stdout)
            self.assertIn("--help", result.stdout)
