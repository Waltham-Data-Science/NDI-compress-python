import sys
import platform
import os

def get_binary_path():
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

    if platform.system().lower() == "windows":
        if not exec_path.endswith(".exe"):
            path_exe = exec_path + ".exe"
            # If exec_path doesn't exist but .exe does, use that
            # Or just append .exe always if on windows?
            # The previous code checked: if not path.endswith('.exe') ... if os.path.exists(path_exe)
            # But normally we just want to run it.
            # I'll stick to appending .exe if missing.
            exec_path = path_exe

    if not os.path.exists(exec_path):
        raise FileNotFoundError(f"Executable not found: {exec_path}")

    return exec_path
