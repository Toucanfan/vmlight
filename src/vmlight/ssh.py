from pathlib import Path


class SshKeyManager:
    """
    Manages the list of SSH keys available for deployment.
    """

    def __init__(self, config) -> None:
        self.key_list_file = Path(config["deploy"]["ssh_key_list_file"])
        if not self.key_list_file.exists():
            raise EnvironmentError("SSH key store file doesn't exist!")
        self.keys = self.key_list_file.read_text().splitlines()
        self.keys = [
            k.split(" ", maxsplit=2) for k in self.keys if (k and not k.startswith("#"))
        ]

    def _write_key_list(self):
        with self.key_list_file.open("w") as f:
            f.write("# Put your SSH keys here\n")
            for k in self.keys:
                f.write(f"{k[0]} {k[1]} {k[2]}\n")

    def add_key(self, key_text: str):
        """
        Add a new SSH key to the store.
        """
        key_type, key, key_name = key_text.split(" ", maxsplit=2)
        for k in self.keys:
            if k[2] == key_name:
                raise ValueError(
                    f"A key with the name {key_name} already exists in the store."
                )
        self.keys.append([key_type, key, key_name])  # type: ignore
        self._write_key_list()

    def add_key_from_file(self, file: Path):
        """
        Add a new SSH key to the store from a file.
        """
        key_lines = file.read_text().splitlines()
        for k in key_lines:
            if not k.startswith("#"):
                self.add_key(k)

    def remove_key(self, key_name: str):
        """
        Remove an SSH key from the store.
        """
        for i, k in enumerate(self.keys):
            if k[2] == key_name:
                self.keys.pop(i)
                self._write_key_list()
                return
        raise ValueError(f"Key with name {key_name} not found in the store.")

    def list_keys(self):
        """
        List all SSH keys in the store.
        """
        print(f"{'NAME':<30} {'TYPE':<10} {'FINGERPRINT'}")
        for k in self.keys:
            fingerprint = k[1][:16]  # Shorten the fingerprint for display
            print(f"{k[2]:<30} {k[0]:<10} {fingerprint}")
