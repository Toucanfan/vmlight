from .utils import ApplicationError, sh
from .helpers import VmBackendHelper
from . import deploy
from pathlib import Path
import subprocess

XENCFG_TEMPLATE = """
# This configures a PVH rather than PV guest
type = "pvh"

# Guest name
name = "{vm_id}-{name}"

# 128-bit UUID for the domain as a hexadecimal number.
# Use "uuidgen" to generate one if required.
# The default behavior is to generate a new UUID each time the guest is started.
#uuid = "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"

# Kernel image to boot
kernel = "{pvgrub_path}"

# Initial memory allocation (MB)
memory = {memory}

# Number of VCPUS
vcpus = {vcpus}

# Network devices
# A list of 'vifspec' entries as described in
# docs/misc/xl-network-configuration.markdown
vif = [ 'vifname=vm{vm_id},ip={ip}' ]

# Disk Devices
# A list of `diskspec' entries as described in
# docs/misc/xl-disk-configuration.txt
disk = [ '{disk_image},{disk_format},xvda,rw' ]
"""

NETWORK_CONFIG_TEMPLATE = """
[Match]
Name=enX0

[Network]
Address={ip}/32
Gateway={gateway}

[Route]
Destination={gateway}/32
"""


class XenVmHelper(VmBackendHelper):
    def __init__(self, vm, config):
        super().__init__(vm, config)
        self.xl_path = Path(config["xen"]["xl_path"]).absolute()
        self.instances_dir = Path(config["general"]["instances_dir"]).absolute()

    def _get_xen_domain_id(self):
        """
        Get the domain ID of a Xen VM.
        """
        try:
            result = sh(f"{self.xl_path} list")
            lines = result.splitlines()
            for line in lines[1:]:  # Skip the header line
                columns = line.split()
                name = columns[0]
                domain_id = columns[1]
                if name.startswith(f"{self.vm.id}-"):
                    return domain_id
            raise ApplicationError(f"A running Xen VM with ID {self.vm.id} not found")
        except subprocess.CalledProcessError as e:
            raise ApplicationError(f"Error executing 'xl list': {e}") from e

    def is_running(self):
        try:
            result = sh(f"{self.xl_path} list")
            lines = result.splitlines()
            for line in lines[1:]:  # Skip the header line
                columns = line.split()
                name = columns[0]
                state = columns[4]
                if name.startswith(f"{self.vm.id}-") and any(
                    l in state for l in ["r", "b"]
                ):
                    return True
            return False
        except subprocess.CalledProcessError as e:
            raise ApplicationError(f"Error executing 'xl list': {e}") from e

    def start(self):
        try:
            sh(
                f"{self.xl_path} create {self.instances_dir / f'{self.vm.id}-{self.vm.name}' / 'xen_vm.cfg'}"
            )
            return True
        except ApplicationError as e:
            raise ApplicationError(f"Error starting Xen VM: {e}") from e

    def stop(self):
        try:
            domain_id = self._get_xen_domain_id()
            sh(f"{self.xl_path} shutdown {domain_id}")
            return True
        except ApplicationError as e:
            raise ApplicationError(f"Error stopping Xen VM: {e}") from e

    def restart(self):
        try:
            domain_id = self._get_xen_domain_id()
            sh(f"{self.xl_path} reboot {domain_id}")
            return True
        except ApplicationError as e:
            raise ApplicationError(f"Error restarting Xen VM: {e}") from e

    def delete(self):
        auto_dir = Path(self.config["xen"]["conf_dir"]) / "auto"
        sh(f"rm -f {auto_dir / f'{self.vm.id}-{self.vm.name}'}")


class XenDeployManager(deploy.DeployManager):
    def __init__(self, args, config):
        self.xenconf_dir = Path(config["xen"]["conf_dir"]).absolute()
        if not self.xenconf_dir.exists():
            raise ApplicationError(
                f"Xen configuration directory does not exist: {self.xenconf_dir}"
            )

        super().__init__(args, config)

    def _setup_instance_paths(self):
        super()._setup_instance_paths()
        self.instance_config_file = self.instance_dir / "xen_vm.cfg"
        self.xen_autostart_dir = self.xenconf_dir / "auto"
        self.xen_autostart_file = (
            self.xen_autostart_dir / f"{self.vm_id}-{self.instance_name}"
        )

    def _get_disk_file_name(self):
        return "root.qcow2"

    def create_instance_config(self):
        disk_format = self.disk_file.suffix.lstrip(".").lower()
        disk_format = "qcow2" if disk_format == "qcow" else disk_format
        disk_format = "raw" if disk_format == "img" else disk_format
        if disk_format not in ["qcow2", "raw"]:
            raise ApplicationError(f"Unsupported disk format: {disk_format}")

        with open(self.instance_config_file, "w") as f:
            f.write(
                XENCFG_TEMPLATE.format(
                    vm_id=self.vm_id,
                    name=self.instance_name,
                    memory=self.args["memory"],
                    vcpus=self.args["vcpus"],
                    ip=self.args["ip"],
                    disk_image=self.disk_file.absolute().as_posix(),
                    disk_format=disk_format,
                    pvgrub_path=self.config["xen"]["pvgrub_path"],
                )
            )

    def enable_instance_autostart(self):
        self.xen_autostart_dir.mkdir(parents=True, exist_ok=True)
        self.xen_autostart_file.symlink_to(self.instance_config_file)

    def deploy_network_config(self):
        network_config_file = self.mount_point / "etc/systemd/network/10-enX0.network"
        network_config_file.parent.mkdir(parents=True, exist_ok=True)
        network_config_file.write_text(
            NETWORK_CONFIG_TEMPLATE.format(
                ip=self.args["ip"],
                gateway=self.config["deploy"]["default_gateway"],
            )
        )

    def cleanup_backend_specific(self):
        self.instance_config_file.unlink()
        self.xen_autostart_file.unlink()
