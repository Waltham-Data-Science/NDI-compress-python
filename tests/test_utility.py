import os

import ndicompress.utility as utility


def test_ndi_bin_path_override(monkeypatch, tmp_path):
    """Setting NDI_BIN_PATH points the binary search at that directory."""
    exe = tmp_path / "ndi_compress_digital"
    exe.write_text("#!/bin/sh\n")
    exe.chmod(0o755)

    monkeypatch.setenv("NDI_BIN_PATH", str(tmp_path))
    assert utility.get_binary_path() == str(tmp_path)
    assert utility.get_executable_path("ndi_compress_digital") == str(exe)


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
