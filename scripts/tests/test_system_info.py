"""Probe availability, output capture and timeout at the subprocess boundary."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import collect_system_info  # noqa: E402


class SystemInfoTests(unittest.TestCase):
    def test_cli_rejects_nonfinite_timeout_without_output_files(self):
        for value in ("nan", "inf"):
            with self.subTest(timeout=value), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                result = subprocess.run(
                    [sys.executable, str(Path(collect_system_info.__file__)), "--timeout", value,
                     "--json", str(root / "system.json"), "--text", str(root / "system.txt")],
                    env={**os.environ, "PATH": ""}, capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse(list(root.iterdir()))

    def test_probe_captures_process_status_and_output(self):
        result = collect_system_info.run_command(
            [sys.executable, "-c", "import sys; print('ready'); print('notice', file=sys.stderr); sys.exit(3)"], 5,
        )
        self.assertTrue(result["available"])
        self.assertEqual(result["returncode"], 3)
        self.assertEqual(result["stdout"], "ready")
        self.assertEqual(result["stderr"], "notice")

    def test_missing_probe_is_reported_as_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            result = collect_system_info.run_command([str(Path(directory) / "missing-probe")], 5)
        self.assertFalse(result["available"])
        self.assertIsNone(result["returncode"])

    def test_probe_timeout_is_recorded(self):
        result = collect_system_info.run_command(
            [sys.executable, "-c", "import time; time.sleep(10)"], 0.05,
        )
        self.assertTrue(result["available"])
        self.assertIsNone(result["returncode"])
        self.assertIn("TimeoutExpired", result["stderr"])


if __name__ == "__main__":
    unittest.main()
