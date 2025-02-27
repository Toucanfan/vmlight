import subprocess


def sh(cmd: str):
    """
    Execute a command and return the output.
    """
    cmdlist = cmd.split(" ")
    return subprocess.check_output(cmdlist).decode("utf-8")
