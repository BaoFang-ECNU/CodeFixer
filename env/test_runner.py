"""Run tests in an isolated repair workspace."""

from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
import time
import traceback
import types
from dataclasses import dataclass
from importlib import util
from pathlib import Path


@dataclass
class TestResult:
    """Result returned by a test command."""

    __test__ = False

    command: str
    returncode: int
    stdout: str
    stderr: str
    duration_sec: float
    timed_out: bool = False

    @property
    def passed(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    @property
    def output(self) -> str:
        return "\n".join(part for part in [self.stdout, self.stderr] if part)


class TestRunner:
    """Execute test commands with timeouts and Python interpreter normalization."""

    def __init__(self, timeout_sec: int = 20):
        self.timeout_sec = timeout_sec

    def run(self, command: str, cwd: Path) -> TestResult:
        args = self._normalize_command(command)
        if "pytest" in args and util.find_spec("pytest") is None:
            return self._run_minipytest(args, cwd)
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                args,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                check=False,
            )
            duration = time.perf_counter() - started
            return TestResult(command=" ".join(args), returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr, duration_sec=duration)
        except subprocess.TimeoutExpired as exc:
            duration = time.perf_counter() - started
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            return TestResult(command=" ".join(args), returncode=124, stdout=stdout, stderr=stderr, duration_sec=duration, timed_out=True)

    @staticmethod
    def _normalize_command(command: str) -> list[str]:
        parts = shlex.split(command, posix=False)
        if parts and parts[0].lower() in {"python", "python3"}:
            parts[0] = sys.executable
        if parts and parts[0].lower() in {"node", "node.exe"} and shutil.which(parts[0]) is None:
            bundled = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "node" / "bin" / "node.exe"
            if bundled.exists():
                parts[0] = str(bundled)
        return parts

    def _run_minipytest(self, args: list[str], cwd: Path) -> TestResult:
        """Run simple test_*.py files when pytest is not installed."""

        started = time.perf_counter()
        test_files = [part for part in args if part.endswith(".py")]
        if not test_files:
            test_files = [path.name for path in cwd.glob("test_*.py")]
        old_path = list(sys.path)
        old_modules = dict(sys.modules)
        stdout_lines: list[str] = []
        failures: list[str] = []
        try:
            sys.path.insert(0, str(cwd))
            sys.modules["pytest"] = self._pytest_shim()
            for name in list(sys.modules):
                if name == "buggy_code" or name.startswith("test_"):
                    sys.modules.pop(name, None)
            total = 0
            for test_file in test_files:
                module_name = Path(test_file).stem
                spec = util.spec_from_file_location(module_name, cwd / test_file)
                if spec is None or spec.loader is None:
                    failures.append(f"cannot load {test_file}")
                    continue
                module = util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                for attr in dir(module):
                    if attr.startswith("test_") and callable(getattr(module, attr)):
                        total += 1
                        try:
                            getattr(module, attr)()
                        except Exception:
                            failures.append(f"{module_name}.{attr}\n{traceback.format_exc()}")
            stdout_lines.append(f"mini-pytest collected {total} tests")
            if failures:
                stdout_lines.append(f"{len(failures)} failed")
                return TestResult(" ".join(args), 1, "\n".join(stdout_lines), "\n".join(failures), time.perf_counter() - started)
            stdout_lines.append("all passed")
            return TestResult(" ".join(args), 0, "\n".join(stdout_lines), "", time.perf_counter() - started)
        finally:
            sys.path[:] = old_path
            for name in list(sys.modules):
                if name not in old_modules:
                    sys.modules.pop(name, None)
            sys.modules.update(old_modules)

    @staticmethod
    def _pytest_shim():
        class RaisesContext:
            def __init__(self, expected):
                self.expected = expected

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                if exc_type is None:
                    raise AssertionError(f"expected {self.expected.__name__} to be raised")
                return issubclass(exc_type, self.expected)

        return types.SimpleNamespace(raises=lambda expected: RaisesContext(expected))
