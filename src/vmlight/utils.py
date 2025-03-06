import subprocess
import os
import sys


class VmlightError(Exception):
    """
    Base class for all Vmlight exceptions.
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class ApplicationError(VmlightError):
    """
    Exception raised for errors in the application.
    """


def sh(cmd: str, error_ok: bool = False) -> str:
    """
    Execute a command and return the output.
    """
    cmdlist = cmd.split(" ")
    try:
        return subprocess.check_output(cmdlist).decode("utf-8")
    except subprocess.CalledProcessError as e:
        if not error_ok:
            raise ApplicationError(f"Command failed: {cmd}: return code {e.returncode}")
        return ""


def require_root():
    """
    Check if the script is running with root privileges.
    """
    if os.geteuid() != 0:
        print("Not running as root, aborting.")
        sys.exit(1)
