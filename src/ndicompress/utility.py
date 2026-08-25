import sys
import platform
import os

def get_binary_path():
    # Allow pointing at a locally rebuilt codec via NDI_BIN_PATH; otherwise use
    # the vendored binaries shipped under bin/<platform> next to this file.
    override = os.environ.get("NDI_BIN_PATH")
    if override:
        return override

    system = platform.system().lower()
    if system == "linux":
        dirname = "linux"
    elif system == "darwin":
        dirname = "macos"
    elif system == "windows":
        dirname = "windows"
    else:
        raise OSError(f"Unsupported operating system: {system}")

    # Path relative to this file
    base_path = os.path.dirname(__file__)
    bin_path = os.path.join(base_path, "bin", dirname)
    return bin_path

def get_executable_path(exec_name):
    bin_path = get_binary_path()
    exec_path = os.path.join(bin_path, exec_name)

    # Candidates in preference order. The vendored Windows codecs all ship as
    # `<name>.exe`, so that is tried first; but NDI_BIN_PATH exists precisely to
    # point at a locally rebuilt codec, which need not carry the extension, so
    # the exact name remains a fallback. Appending `.exe` unconditionally made
    # the override unusable on Windows and reported a path the caller never named.
    candidates = [exec_path]
    if platform.system().lower() == "windows" and not exec_path.endswith(".exe"):
        candidates.insert(0, exec_path + ".exe")

    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    raise FileNotFoundError("Executable not found: " + " or ".join(candidates))
