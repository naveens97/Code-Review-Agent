from executor.local_sandbox import LocalSandboxExecutor


def make_executor(timeout=3, memory_mb=64):
    return LocalSandboxExecutor(timeout_seconds=timeout, memory_mb=memory_mb)


def test_hello_world_succeeds():
    result = make_executor().execute('print("Hello, World!")')
    assert result["success"] is True
    assert result["exit_code"] == 0
    assert result["stdout"] == "Hello, World!\n"
    assert result["timed_out"] is False


def test_stdin_is_passed_through():
    result = make_executor().execute(
        'name = input()\nprint(f"Hi {name}")', stdin="Naveen"
    )
    assert result["success"] is True
    assert result["stdout"] == "Hi Naveen\n"


def test_runtime_error_reports_nonzero_exit_and_stderr():
    result = make_executor().execute("x = 1 / 0")
    assert result["success"] is False
    assert result["exit_code"] != 0
    assert "ZeroDivisionError" in result["stderr"]


def test_infinite_loop_times_out_instead_of_hanging():
    result = make_executor(timeout=2).execute("while True:\n    pass")
    assert result["timed_out"] is True
    assert result["success"] is False
    assert result["execution_time_ms"] < 4000  # bounded, not actually infinite


def test_memory_limit_is_enforced():
    code = 'x = []\nwhile True:\n    x.append(" " * 10**7)'
    result = make_executor(timeout=5, memory_mb=64).execute(code)
    assert result["success"] is False
    assert result["timed_out"] is False  # should fail fast on memory, not time out
    assert result["execution_time_ms"] < 3000


def test_unsupported_language_returns_clean_error_not_a_crash():
    result = make_executor().execute("console.log(1)", language="javascript")
    assert result["success"] is False
    assert "javascript" in result["stderr"].lower()


def test_output_is_truncated_beyond_max_chars():
    ex = LocalSandboxExecutor(timeout_seconds=5, memory_mb=64, max_output_chars=100)
    result = ex.execute('print("x" * 1000)')
    assert len(result["stdout"]) < 1000
    assert "truncated" in result["stdout"]
