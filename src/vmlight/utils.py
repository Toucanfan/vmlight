import subprocess
import os
import sys


def sh(cmd: str):
    """
    Execute a command and return the output.
    """
    cmdlist = cmd.split(" ")
    return subprocess.check_output(cmdlist).decode("utf-8")


def require_root():
    """
    Check if the script is running with root privileges.
    """
    if os.geteuid() != 0:
        print("Not running as root, aborting.")
        sys.exit(1)
