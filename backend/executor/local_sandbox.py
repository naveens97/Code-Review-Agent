"""
Local, subprocess-based code executor.

WHAT THIS PROTECTS AGAINST
  - Infinite loops / runaway CPU usage (wall-clock timeout + CPU rlimit)
  - Memory exhaustion (address-space rlimit)
  - Fork bombs / runaway process spawning (process-count rlimit)
  - Excessive disk writes (file-size rlimit)
  - Oversized output flooding the response (output truncation)

WHAT THIS DOES NOT PROTECT AGAINST
  - Filesystem access within the server process's own OS permissions
  - Network access from the executed code
  - Kernel-level sandbox escapes

SUPPORTED LANGUAGES (local mode)
  python      -- sys.executable (same interpreter that runs Flask)
  javascript  -- node (must be on PATH)
  java        -- javac + java (JDK must be on PATH)
  c           -- gcc (must be on PATH)
  cpp         -- g++ (must be on PATH)

This is a development-grade sandbox suitable for local use, demos, and
trusted users. It runs submitted code with the SAME OS-level permissions
as the Flask process. Do not expose this to untrusted public users without
adding real isolation -- run the whole backend in a container with
--network=none and a read-only filesystem (see the Dockerfile), or swap in
the Judge0 provider (executor/judge0_provider.py), which executes code in
disposable, network-isolated containers on Judge0's infrastructure instead
of this host.
"""
import os
import subprocess
import sys
import tempfile
import time

from .base import BaseExecutor

IS_POSIX = os.name == "posix"

if IS_POSIX:
    import resource


def _limit_resources(memory_mb: int, cpu_seconds: int):
    """Runs in the child process, after fork, before exec. Only meaningful
    on POSIX systems (Linux/macOS); Windows has no equivalent rlimit API,
    so on Windows we fall back to timeout-only protection."""
    def _apply():
        try:
            mem_bytes = memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
            resource.setrlimit(resource.RLIMIT_NPROC, (32, 32))
            resource.setrlimit(resource.RLIMIT_FSIZE, (2 * 1024 * 1024, 2 * 1024 * 1024))
            os.setsid()
        except (ValueError, OSError):
            # Some limits aren't settable in every environment (e.g. some
            # containers restrict RLIMIT_NPROC further already) -- better to
            # run with partial limits than to crash the request entirely.
            pass
    return _apply


# ---------------------------------------------------------------------------
# Compiler / runtime discovery.
#
# On POSIX the tools are usually on PATH already.  On Windows they are
# often installed into well-known directories but *not* added to PATH.
# _find_tool() probes a list of candidate locations and returns the first
# that exists.  It caches the result so the filesystem scan happens at
# most once per tool per process lifetime.
# ---------------------------------------------------------------------------
import glob
import shutil

_tool_cache: dict[str, str | None] = {}

# Candidate directories to probe, keyed by tool basename (without .exe).
# Order matters — first match wins.
_WIN_SEARCH_PATHS: dict[str, list[str]] = {
    "javac": [
        os.path.join(os.environ.get("JAVA_HOME", ""), "bin"),
        # Common JDK install locations on Windows
        *sorted(glob.glob(r"C:\jdk21\jdk-*\bin"), reverse=True),
        *sorted(glob.glob(r"C:\Program Files\Java\jdk-*\bin"), reverse=True),
        *sorted(glob.glob(r"C:\Program Files\Eclipse Adoptium\jdk-*\bin"), reverse=True),
        *sorted(glob.glob(r"C:\Program Files\Microsoft\jdk-*\bin"), reverse=True),
        *sorted(glob.glob(r"C:\Program Files\Amazon Corretto\jdk*\bin"), reverse=True),
        *sorted(glob.glob(r"C:\Program Files\Zulu\zulu-*\bin"), reverse=True),
    ],
    "java": [
        os.path.join(os.environ.get("JAVA_HOME", ""), "bin"),
        *sorted(glob.glob(r"C:\jdk21\jdk-*\bin"), reverse=True),
        *sorted(glob.glob(r"C:\Program Files\Java\jdk-*\bin"), reverse=True),
        *sorted(glob.glob(r"C:\Program Files\Eclipse Adoptium\jdk-*\bin"), reverse=True),
        *sorted(glob.glob(r"C:\Program Files\Microsoft\jdk-*\bin"), reverse=True),
        *sorted(glob.glob(r"C:\Program Files\Amazon Corretto\jdk*\bin"), reverse=True),
        *sorted(glob.glob(r"C:\Program Files\Zulu\zulu-*\bin"), reverse=True),
        *sorted(glob.glob(r"C:\Program Files\Java\jre-*\bin"), reverse=True),
    ],
    "gcc": [
        *sorted(glob.glob(r"C:\msys64\mingw64\bin"), reverse=True),
        *sorted(glob.glob(r"C:\msys64\ucrt64\bin"), reverse=True),
        *sorted(glob.glob(r"C:\mingw64\bin"), reverse=True),
        *sorted(glob.glob(r"C:\MinGW\bin"), reverse=True),
        *sorted(glob.glob(r"C:\TDM-GCC-*\bin"), reverse=True),
        *sorted(glob.glob(r"C:\Program Files\mingw-w64\*\mingw64\bin"), reverse=True),
    ],
    "g++": [
        *sorted(glob.glob(r"C:\msys64\mingw64\bin"), reverse=True),
        *sorted(glob.glob(r"C:\msys64\ucrt64\bin"), reverse=True),
        *sorted(glob.glob(r"C:\mingw64\bin"), reverse=True),
        *sorted(glob.glob(r"C:\MinGW\bin"), reverse=True),
        *sorted(glob.glob(r"C:\TDM-GCC-*\bin"), reverse=True),
        *sorted(glob.glob(r"C:\Program Files\mingw-w64\*\mingw64\bin"), reverse=True),
    ],
}

# Per-language installation instructions shown when a tool can't be found.
_INSTALL_HINTS: dict[str, str] = {
    "javac": (
        "Install a JDK (Java Development Kit) to compile and run Java code.\n"
        "Recommended: Download from https://adoptium.net/ (Eclipse Temurin)\n"
        "or run:  winget install EclipseAdoptium.Temurin.21.JDK"
    ),
    "java": (
        "Install a JDK (Java Development Kit) to run Java code.\n"
        "Recommended: Download from https://adoptium.net/ (Eclipse Temurin)\n"
        "or run:  winget install EclipseAdoptium.Temurin.21.JDK"
    ),
    "gcc": (
        "Install MinGW-w64 or MSYS2 to compile and run C code.\n"
        "Recommended: Download MSYS2 from https://www.msys2.org/\n"
        "then run:  pacman -S mingw-w64-ucrt-x86_64-gcc\n"
        "Or:  winget install MSYS2.MSYS2"
    ),
    "g++": (
        "Install MinGW-w64 or MSYS2 to compile and run C++ code.\n"
        "Recommended: Download MSYS2 from https://www.msys2.org/\n"
        "then run:  pacman -S mingw-w64-ucrt-x86_64-gcc\n"
        "Or:  winget install MSYS2.MSYS2"
    ),
}


def _find_tool(name: str) -> str:
    """Return the full path to a tool, searching PATH first and then
    well-known Windows install directories.  Returns the bare name as a
    fallback (subprocess will raise FileNotFoundError later)."""
    if name in _tool_cache:
        cached = _tool_cache[name]
        return cached if cached is not None else name

    # 1. Try PATH first (works on all OSes, and on Windows when the
    #    user has properly configured their environment).
    found = shutil.which(name)
    if found:
        _tool_cache[name] = found
        return found

    # 2. On Windows, probe well-known directories.
    if os.name == "nt":
        exe_name = name if name.endswith(".exe") else name + ".exe"
        for directory in _WIN_SEARCH_PATHS.get(name, []):
            candidate = os.path.join(directory, exe_name)
            if os.path.isfile(candidate):
                _tool_cache[name] = candidate
                return candidate

    # 3. Not found anywhere — cache the miss and return the bare name
    #    so the caller gets a clear FileNotFoundError from subprocess.
    _tool_cache[name] = None
    return name


# ---------------------------------------------------------------------------
# Per-language runtime configs.
# Each entry is (filename, run_cmd_factory, compile_cmd_factory_or_None).
#
# run_cmd_factory(tmpdir, filename)     -> list[str]  command to *run* the code
# compile_cmd_factory(tmpdir, filename) -> list[str]  command to compile first
#                                         (None means interpret directly)
# ---------------------------------------------------------------------------
_LANGUAGE_CONFIGS = {
    "python": {
        "filename": "submission.py",
        "run": lambda d, f: [sys.executable, "-I", "-S", os.path.join(d, f)],
        "compile": None,
    },
    "javascript": {
        "filename": "submission.js",
        "run": lambda d, f: [_find_tool("node"), os.path.join(d, f)],
        "compile": None,
    },
    "java": {
        # Java: the public class must match the filename.
        # We require exactly one public class named 'Main'.
        "filename": "Main.java",
        "compile": lambda d, f: [_find_tool("javac"), os.path.join(d, f)],
        # After compilation, run `java -cp <tmpdir> Main`
        "run": lambda d, f: [_find_tool("java"), "-cp", d, "Main"],
    },
    "c": {
        "filename": "submission.c",
        "compile": lambda d, f: [_find_tool("gcc"), "-Wall", "-Wextra", "-o",
                                  os.path.join(d, "submission.exe" if os.name == "nt" else "submission"),
                                  os.path.join(d, f)],
        "run": lambda d, f: [os.path.join(d, "submission.exe" if os.name == "nt" else "submission")],
    },
    "cpp": {
        "filename": "submission.cpp",
        "compile": lambda d, f: [_find_tool("g++"), "-Wall", "-Wextra", "-std=c++17", "-o",
                                   os.path.join(d, "submission.exe" if os.name == "nt" else "submission"),
                                   os.path.join(d, f)],
        "run": lambda d, f: [os.path.join(d, "submission.exe" if os.name == "nt" else "submission")],
    },
}


class LocalSandboxExecutor(BaseExecutor):
    """Executes submitted code in a temp directory using the host's installed
    compilers / runtimes.  See module docstring for supported languages and
    security caveats."""

    def __init__(self, timeout_seconds=8, memory_mb=128, max_output_chars=20_000):
        self.timeout_seconds = timeout_seconds
        self.memory_mb = memory_mb
        self.max_output_chars = max_output_chars

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def execute(self, code: str, language: str = "python", stdin: str = "") -> dict:
        config = _LANGUAGE_CONFIGS.get(language)
        if config is None:
            supported = ", ".join(sorted(_LANGUAGE_CONFIGS))
            return {
                "success": False, "stdout": "", "timed_out": False, "exit_code": -1,
                "execution_time_ms": 0,
                "stderr": (
                    f"'{language}' is not supported by the local executor. "
                    f"Supported languages: {supported}. "
                    "Configure EXECUTION_PROVIDER=judge0 for broader language support."
                ),
            }

        with tempfile.TemporaryDirectory() as tmpdir:
            filename = config["filename"]
            src_path = os.path.join(tmpdir, filename)
            with open(src_path, "w", encoding="utf-8") as fh:
                fh.write(code)

            # -- Compile step (compiled languages only) ------------------
            if config.get("compile") is not None:
                compile_result = self._compile(config["compile"](tmpdir, filename), tmpdir)
                if compile_result is not None:
                    return compile_result   # compilation failed; surface the error

            # -- Run step ------------------------------------------------
            run_cmd = config["run"](tmpdir, filename)
            return self._run(run_cmd, tmpdir, stdin)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _compile(self, cmd: list, cwd: str) -> dict | None:
        """Run a compilation command.  Returns None on success, or an error
        result dict (matching the execute() schema) if compilation fails."""
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                cwd=cwd,
            )
        except FileNotFoundError as e:
            tool = cmd[0] if cmd else "compiler"
            # Extract the bare tool name for the install hint lookup.
            tool_basename = os.path.basename(tool).replace(".exe", "")
            hint = _INSTALL_HINTS.get(tool_basename, "")
            return {
                "success": False, "stdout": "", "timed_out": False, "exit_code": -1,
                "execution_time_ms": 0,
                "stderr": (
                    f"Compiler not found: '{tool_basename}'.\n\n"
                    f"{hint}\n\n"
                    "After installing, restart the backend server so it can "
                    "discover the new tool."
                ).strip(),
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False, "stdout": "", "timed_out": True, "exit_code": -1,
                "execution_time_ms": self.timeout_seconds * 1000,
                "stderr": f"Compilation timed out after {self.timeout_seconds}s.",
            }

        if proc.returncode != 0:
            # Surface compiler errors verbatim as stderr -- they are already
            # in the right format for the user (line numbers, messages, etc.).
            combined = (proc.stderr or "") or (proc.stdout or "")
            return {
                "success": False,
                "stdout": "",
                "stderr": self._truncate(combined.strip() or "Compilation failed (no output)."),
                "exit_code": proc.returncode,
                "execution_time_ms": 0,
                "timed_out": False,
            }
        return None  # success

    def _run(self, cmd: list, cwd: str, stdin: str) -> dict:
        """Execute an already-compiled (or interpreted) program and return
        the standard result dict."""
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        preexec = _limit_resources(self.memory_mb, self.timeout_seconds + 2) if IS_POSIX else None

        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                cwd=cwd,
                env=env,
                preexec_fn=preexec,
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return {
                "success": proc.returncode == 0,
                "stdout": self._truncate(proc.stdout),
                "stderr": self._truncate(proc.stderr),
                "exit_code": proc.returncode,
                "execution_time_ms": elapsed_ms,
                "timed_out": False,
            }
        except subprocess.TimeoutExpired as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            partial = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", "replace")
            return {
                "success": False,
                "stdout": self._truncate(partial),
                "stderr": (
                    f"Execution timed out after {self.timeout_seconds}s. "
                    "Check for infinite loops or unbounded recursion."
                ),
                "exit_code": -1,
                "execution_time_ms": elapsed_ms,
                "timed_out": True,
            }
        except (OSError, FileNotFoundError) as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return {
                "success": False, "stdout": "",
                "stderr": f"Failed to start execution: {exc}",
                "exit_code": -1, "execution_time_ms": elapsed_ms, "timed_out": False,
            }

    def _truncate(self, text: str) -> str:
        if not text:
            return ""
        if len(text) > self.max_output_chars:
            return text[: self.max_output_chars] + f"\n... [output truncated at {self.max_output_chars} characters]"
        return text
