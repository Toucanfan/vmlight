from pathlib import Path
import deploy

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


class XenDeployAgent(deploy.DeployAgent):
    def __init__(self, args, config):
        if not Path("/usr/sbin/xl").exists():
            raise EnvironmentError("xl toolstack is not installed.")

        with open("/proc/xen/capabilities", "r") as f:
            if "control_d" not in f.read():
                raise EnvironmentError("Xen hypervisor is not running.")

        super().__init__(args, config)

        self.xenconf_dir = Path(self.config["xen"]["xenconf_dir"]).absolute()
        if not self.xenconf_dir.exists():
            raise EnvironmentError(
                f"Xen configuration directory does not exist: {self.xenconf_dir}"
            )
        self.instance_config_file = self.instance_dir / "xen_vm.cfg"
        self.xen_autostart_dir = self.xenconf_dir / "auto"
        self.xen_autostart_file = (
            self.xen_autostart_dir / f"{self.vm_id}-{self.instance_name}"
        )

    def create_instance_config(self):
        disk_format = self.disk_file.suffix.lstrip(".").lower()
        disk_format = "qcow2" if disk_format == "qcow" else disk_format
        disk_format = "raw" if disk_format == "img" else disk_format
        if disk_format not in ["qcow2", "raw"]:
            raise ValueError(f"Unsupported disk format: {disk_format}")

        with open(self.instance_config_file, "w") as f:
            f.write(
                XENCFG_TEMPLATE.format(
                    vm_id=self.vm_id,
                    name=self.instance_name,
                    memory=self.args.deploy["memory"],
                    vcpus=self.args.deploy["vcpus"],
                    ip=self.args.deploy["ip"],
                    disk_image=self.disk_file,
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
                ip=self.args.deploy["ip"],
                gateway=self.config["deploy"]["default_gateway"],
            )
        )

    def cleanup_backend_specific(self):
        self.instance_config_file.unlink()
        self.xen_autostart_file.unlink()
