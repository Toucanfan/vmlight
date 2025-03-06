from .utils import ApplicationError
from pathlib import Path

from .image import ImageManager
from .ssh import SshKeyManager
from .utils import sh


class DeployManager:
    """
    Object that handles the deployment of an instance.
    Should not be instantiated directly, but rather through a backend specific class
    that inherits from this class.
    """

    def __init__(self, args, config):
        """
        Initialize the deploy manager.
        """
        self.args = args.__dict__.copy()
        self.config = config
        self.instances_dir = Path(self.config["general"]["instances_dir"]).absolute()
        self.instances_dir.mkdir(parents=True, exist_ok=True)
        self.image_dir = Path(self.config["general"]["image_dir"]).absolute()
        self.image_dir.mkdir(parents=True, exist_ok=True)
        self._setup_instance_paths()

    def _setup_instance_paths(self):
        self.instance_name = self.args["name"]
        self.vm_id = self.get_available_vm_id()
        self.instance_dir = self.instances_dir / f"{self.vm_id}-{self.instance_name}"
        self.disk_file = self.instance_dir / "root.qcow2"
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

    def interactive_deploy(self):
        """
        Deploy the instance in interactive mode.
        """
        # Handle required arguments
        if not self.args.get("name"):
            self.args["name"] = input("Please enter a name for the instance: ")
            self._setup_instance_paths()  # update instance paths (an ugly hack, yes)

        # Handle image selection from available images
        if not self.args.get("image"):
            image_manager = ImageManager(self.config)
            if not image_manager.images:
                raise ApplicationError("No images available.")
            print("Available images:")
            image_manager.list()
            image_choice = int(input("Please select an image by number: ")) - 1
            self.args["image"] = image_manager.images[image_choice].stem

        # Handle IP address
        if not self.args.get("ip"):
            self.args["ip"] = input("Please give the instance an IP address: ")

        # Handle SSH key selection from available keys
        if not self.args.get("ssh_key"):
            self.args["ssh_key"] = []
            ssh_key_manager = SshKeyManager(self.config)
            if ssh_key_manager.keys:
                print("Available SSH keys:")
                ssh_key_manager.list_keys()
                while True:
                    key_choice = input(
                        "Please select an SSH key by number (or press Enter to continue): "
                    )
                    if key_choice:
                        key_choice = int(key_choice) - 1
                        self.args["ssh_key"].append(ssh_key_manager.keys[key_choice][2])
                    else:
                        break
            else:
                print("No SSH keys available, skipping SSH key selection.")

        # Handle optional arguments
        user_input = input(
            f"Please enter the disk size (default: {self.config['deploy']['disk_size']}): "
        )
        self.args["disk_size"] = (
            user_input if user_input else self.config["deploy"]["disk_size"]
        )

        user_input = input(
            f"Please enter the amount of memory (default: {self.config['deploy']['memory']}): "
        )
        self.args["memory"] = (
            user_input if user_input else self.config["deploy"]["memory"]
        )

        user_input = input(
            f"Please enter the number of vcpus (default: {self.config['deploy']['vcpus']}): "
        )
        self.args["vcpus"] = (
            user_input if user_input else self.config["deploy"]["vcpus"]
        )

        print("Thank you for the information!")

        self.deploy()

    def deploy(self):
        """
        Deploy the instance.
        """
        try:
            print(f"Deploying instance as '{self.vm_id}-{self.instance_name}'")
            print("Creating instance directory...")
            self.create_instance_dir()
            print("Copying image...")
            self.copy_image()
            print("Resizing disk...")
            self.resize_disk()
            print("Creating instance configuration...")
            self.create_instance_config()
            print("Enabling instance autostart...")
            self.enable_instance_autostart()
            print("Mounting disk...")
            self.mount_disk()
            print("Deploying network configuration...")
            self.deploy_network_config()
            print("Deploying SSH keys...")
            self.deploy_ssh_keys()
            print("Setting instance hostname...")
            self.set_instance_hostname()
            print("Umounting disk...")
            self.umount_disk()
            print("Deployment complete!")
        except Exception as e:
            print("An error occurred during deployment, cleaning up...")
            self.umount_disk()
            self.cleanup_backend_specific()
            self.cleanup()
            raise e

    def create_instance_dir(self):
        """
        Create the instance directory.
        """
        self.instance_dir.mkdir(parents=True, exist_ok=True)

    def copy_image(self):
        """
        Copy the image to the instance directory, converting to qcow2 if necessary.
        """
        image_manager = ImageManager(self.config)
        src_file = image_manager.get_path_by_name(self.args["image"])
        dst_file = self.disk_file

        if src_file.suffix == ".img":
            sh(f"qemu-img convert -O qcow2 {src_file} {dst_file}")
        else:
            sh(f"cp {src_file} {dst_file}")

    def resize_disk(self):
        """
        Resize the disk to the specified size.
        """
        sh(f"qemu-img resize {self.disk_file} {self.args['disk_size']}")

    def mount_disk(self):
        """
        Mount the disk to the mount point.
        """
        self.mount_point.mkdir(parents=True, exist_ok=True)
        sh(f"guestmount -a {self.disk_file} -m /dev/sda1 {self.mount_point}")

    def umount_disk(self):
        """
        Umount the disk from the mount point.
        """
        sh(f"umount {self.mount_point}", error_ok=True)
        if self.mount_point.exists():
            self.mount_point.rmdir()

    def cleanup(self):
        """
        Cleanup the instance directory.
        """
        sh(f"rm -rf {self.instance_dir}")

    def deploy_ssh_keys(self):
        """
        Deploy the SSH keys to the instance.
        """
        guest_key_file = self.mount_point / "root/.ssh/authorized_keys"
        guest_key_file.parent.mkdir(parents=True, exist_ok=True)
        guest_key_file.touch(exist_ok=True)
        key_manager = SshKeyManager(self.config)
        for key_name in self.args["ssh_key"]:
            key = key_manager.get_key_by_name(key_name, as_text=True)
            guest_key_file.write_text(key)

    def set_instance_hostname(self):
        """
        Set the instance hostname.
        """
        hostname = self.args["name"]
        with open(self.mount_point / "etc/hostname", "w") as f:
            f.write(hostname)

    def deploy_network_config(self):
        """
        Deploy the network configuration to the instance.
        """
        raise NotImplementedError("deploy_network_config")

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
