from pathlib import Path
from utils import sh


class DeployAgent:
    """
    Object that handles the deployment of an instance.
    Should not be instantiated directly, but rather through a backend specific class
    that inherits from this class.
    """

    def __init__(self, args, config):
        """
        Initialize the deploy agent.
        """
        self.args = args
        self.config = config
        self.instances_dir = Path(self.config["general"]["instances_dir"]).absolute()
        self.instances_dir.mkdir(parents=True, exist_ok=True)
        self.image_dir = Path(self.config["general"]["image_dir"]).absolute()
        self.image_dir.mkdir(parents=True, exist_ok=True)
        self.instance_name = self.args.deploy.name
        self.vm_id = self.get_available_vm_id()
        self.instance_dir = self.instances_dir / f"{self.vm_id}-{self.instance_name}"
        self.disk_file = self.instance_dir / f"root{self.args.deploy.image.suffix}"
        self.mount_point = self.instance_dir / "mnt"

    def get_available_vm_id(self):
        """
        Get the next available VM ID.
        """
        vm_ids = [int(p.name.split("-")[0]) for p in self.instances_dir.glob("*")]
        if not vm_ids:
            return 1
        # Sort the vm_ids and find the first missing number
        vm_ids.sort()
        for i in range(1, len(vm_ids) + 1):
            if i != vm_ids[i - 1]:
                return i
        return len(vm_ids) + 1

    def deploy(self):
        """
        Deploy the instance.
        """
        try:
            self.create_instance_dir()
            self.copy_image()
            self.resize_disk()
            self.create_instance_config()
            self.enable_instance_autostart()
            self.mount_disk()
            self.deploy_network_config()
            self.deploy_ssh_keys()
            self.set_instance_hostname()
            self.umount_disk()
        except Exception as e:
            print(e)
            self.umount_disk()
            self.cleanup_backend_specific()
            self.cleanup()

    def create_instance_dir(self):
        """
        Create the instance directory.
        """
        self.instance_dir.mkdir(parents=True, exist_ok=True)

    def copy_image(self):
        """
        Copy the image to the instance directory.
        """
        src_file = self.image_dir / Path(self.args.deploy.image)
        dst_file = self.disk_file
        sh(f"cp {src_file} {dst_file}")

    def resize_disk(self):
        """
        Resize the disk to the specified size.
        """
        sh(f"qemu-img resize {self.disk_file} {self.args.deploy.disk_size}")

    def mount_disk(self):
        """
        Mount the disk to the mount point.
        """
        self.mount_point.mkdir(parents=True, exist_ok=True)
        sh(f"mount {self.disk_file} {self.mount_point}")

    def umount_disk(self):
        """
        Umount the disk from the mount point.
        """
        sh(f"umount {self.mount_point}")
        self.mount_point.rmdir()

    def cleanup(self):
        """
        Cleanup the instance directory.
        """
        sh(f"rm -rf {self.instance_dir}")

    def deploy_network_config(self):
        """
        Deploy the network configuration to the instance.
        """
        pass

    def deploy_ssh_keys(self):
        """
        Deploy the SSH keys to the instance.
        """
        pass

    def set_instance_hostname(self):
        """
        Set the instance hostname.
        """
        pass

    def create_instance_config(self):
        """
        Create the instance configuration file.
        """
        raise NotImplementedError("create_instance_config")

    def enable_instance_autostart(self):
        """
        Enable the instance autostart.
        """
        raise NotImplementedError("enable_instance_autostart")

    def cleanup_backend_specific(self):
        """
        Do backend specific cleanup.
        """
        raise NotImplementedError("cleanup_backend_specific")
