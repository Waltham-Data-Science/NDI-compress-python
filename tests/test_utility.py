import os
import platform

import pytest

import ndicompress.utility as utility


def _fake_system(monkeypatch, name):
    """Force utility's platform probe to report a given OS on any host.

    Lets the Windows-only branch of get_executable_path() be exercised from
    ubuntu/macos runners too, so a Windows regression cannot hide until the
    Windows leg of the matrix runs.
    """
    monkeypatch.setattr(platform, "system", lambda: name)


def test_ndi_bin_path_override(monkeypatch, tmp_path):
    """Setting NDI_BIN_PATH points the binary search at that directory."""
    exe = tmp_path / "ndi_compress_digital"
    exe.write_text("#!/bin/sh\n")
    exe.chmod(0o755)

    monkeypatch.setenv("NDI_BIN_PATH", str(tmp_path))
    assert utility.get_binary_path() == str(tmp_path)
    assert utility.get_executable_path("ndi_compress_digital") == str(exe)


def test_windows_prefers_dot_exe(monkeypatch, tmp_path):
    """On Windows the vendored `<name>.exe` wins over a bare `<name>`."""
    _fake_system(monkeypatch, "Windows")
    bare = tmp_path / "ndi_compress_digital"
    bare.write_text("not the real codec\n")
    exe = tmp_path / "ndi_compress_digital.exe"
    exe.write_text("MZ\n")

    monkeypatch.setenv("NDI_BIN_PATH", str(tmp_path))
    assert utility.get_executable_path("ndi_compress_digital") == str(exe)


def test_windows_falls_back_to_extensionless(monkeypatch, tmp_path):
    """On Windows a locally built, extension-less codec still resolves.

    NDI_BIN_PATH exists to point at a rebuilt codec; such a build need not be
    named `.exe`. Appending `.exe` unconditionally made the override unusable
    on Windows.
    """
    _fake_system(monkeypatch, "Windows")
    bare = tmp_path / "ndi_compress_digital"
    bare.write_text("locally built codec\n")

    monkeypatch.setenv("NDI_BIN_PATH", str(tmp_path))
    assert utility.get_executable_path("ndi_compress_digital") == str(bare)


def test_windows_missing_binary_names_every_candidate(monkeypatch, tmp_path):
    """The error must name both paths tried, not just the `.exe` guess."""
    _fake_system(monkeypatch, "Windows")
    monkeypatch.setenv("NDI_BIN_PATH", str(tmp_path))

    with pytest.raises(FileNotFoundError) as excinfo:
        utility.get_executable_path("ndi_compress_digital")

    # Parsed, not substring-matched: the bare path is a prefix of the .exe
    # path, so `bare in message` would pass even if only .exe were reported.
    prefix = "Executable not found: "
    message = str(excinfo.value)
    assert message.startswith(prefix)
    assert message[len(prefix):].split(" or ") == [
        str(tmp_path / "ndi_compress_digital.exe"),
        str(tmp_path / "ndi_compress_digital"),
    ]


def test_non_windows_does_not_append_exe(monkeypatch, tmp_path):
    """Non-Windows hosts resolve the exact name and never invent a `.exe`."""
    _fake_system(monkeypatch, "Linux")
    monkeypatch.setenv("NDI_BIN_PATH", str(tmp_path))

    with pytest.raises(FileNotFoundError) as excinfo:
        utility.get_executable_path("ndi_compress_digital")

    assert ".exe" not in str(excinfo.value)


def test_get_binary_path_default_without_override(monkeypatch):
    """Without the override, the path resolves under the package's bin dir."""
    monkeypatch.delenv("NDI_BIN_PATH", raising=False)
    path = utility.get_binary_path()
    assert path.endswith(os.path.join("bin", "macos")) or "bin" in path


def test_readme_import_name():
    """Doc-drift guard: the README example must import the real package name."""
    readme = os.path.join(os.path.dirname(__file__), "..", "README.md")
    with open(readme, "r") as f:
        content = f.read()
    assert "import ndicompress" in content
    # The old, wrong import name must not reappear.
    assert "import ndi_compress" not in content
