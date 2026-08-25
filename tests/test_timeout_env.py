import warnings

import pytest

import ndicompress.compress as compress


@pytest.mark.parametrize("value", ["0", "-1", "-0.5", "abc"])
def test_nonpositive_or_invalid_timeout_falls_back(monkeypatch, value):
    """0, negative, and unparseable values fall back to the 300s default
    with a RuntimeWarning (0/negative would make subprocess.run fail
    immediately)."""
    monkeypatch.setenv("NDI_COMPRESS_TIMEOUT", value)
    with pytest.warns(RuntimeWarning):
        result = compress._read_timeout_env()
    assert result == 300.0


def test_valid_positive_timeout_used(monkeypatch):
    monkeypatch.setenv("NDI_COMPRESS_TIMEOUT", "12.5")
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # no warning expected for a valid value
        assert compress._read_timeout_env() == 12.5


def test_timeout_read_at_call_time(monkeypatch):
    """The timeout must be resolved per call, so an env var set after import
    takes effect on the next codec call (previously it was frozen at import)."""
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["timeout"] = kwargs.get("timeout")

        class _Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return _Result()

    monkeypatch.setattr(compress.subprocess, "run", fake_run)
    monkeypatch.setattr(compress, "get_executable_path", lambda name: "/bin/true")

    monkeypatch.setenv("NDI_COMPRESS_TIMEOUT", "42")
    compress._call_c_exec("dummy", [])
    assert captured["timeout"] == 42.0

    # Change the env var again after the first call; the next call must honor it.
    monkeypatch.setenv("NDI_COMPRESS_TIMEOUT", "9")
    compress._call_c_exec("dummy", [])
    assert captured["timeout"] == 9.0
