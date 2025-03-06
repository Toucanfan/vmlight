import configparser
import os
import sys
import shutil
from pathlib import Path

from .args import parse_args
from .xen import XenDeployAgent
from .ssh import SshKeyManager
from .image import ImageManager
from .utils import require_root


def get_config():
    """
    Get configuration from INI file or defaults.
    Returns a dictionary with configuration values.
    """
    config_dict = {
        "general": {
            "image_dir": "/var/lib/vmlight/images",
            "instances_dir": "/var/lib/vmlight/instances",
        },
        "deploy": {
            "memory": "512",
            "disk_size": "10G",
            "vcpus": "1",
            "type": "xen",
            "ssh_key_list_file": "/etc/vmlight/ssh_key_store",
            "default_gateway": "10.10.10.2",
        },
        "xen": {
            "conf_dir": "/etc/xen",
            "pvgrub_path": "/usr/lib/xen/bin/pvgrub",
        },
    }

    config_files = [
        os.path.expanduser("~/.config/vmlight.conf"),  # Local user config
        "/etc/vmlight/vmlight.conf",  # Global system config
    ]

    parser = configparser.ConfigParser()
    # Read all config files, later files' values take precedence
    parser.read([f for f in config_files if os.path.exists(f)])

    # Merge config files into config_dict
    for section, section_config in config_dict.items():
        if section in parser:
            settings = parser[section]
            for key in section_config:
                if key in settings:
                    section_config[key] = settings[key]

    return config_dict


def deploy(args, config, subparser):
    """
    Run the 'deploy' command.
    """
    if not args.interactive:
        if not (args.name and args.image and args.ip):
            subparser.error(
                "The following arguments are required for non-interactive mode: --name, --image, --ip"
            )
    require_root()
    if args.type == "xen":
        agent = XenDeployAgent(args, config)
        agent.deploy()

    elif args.type == "kvm":
        print("Deploying a KVM instance")
    elif args.type == "systemd-nspawn":
        print("Deploying a systemd-nspawn instance")


def manage_images(args, config, subparser):
    """
    Run the 'image' command.
    """
    image_manager = ImageManager(config)
    if args.list:
        image_manager.list()
    elif args.add:
        require_root()
        image_manager.add(Path(args.add))
    elif args.remove:
        require_root()
        image_manager.remove(args.remove)
    else:
        subparser.error("No valid argument provided.")


def manage_ssh_keys(args, config, subparser):
    """
    Run the 'ssh-keys' command.
    """
    manager = SshKeyManager(config)
    if args.add:
        require_root()
        manager.add_key(args.add)
    elif args.add_file:
        require_root()
        manager.add_key_from_file(Path(args.add_file))
    elif args.remove:
        require_root()
        manager.remove_key(args.remove)
    elif args.list:
        manager.list_keys()
    else:
        subparser.error("No valid argument provided.")


def check_environment():
    required_binaries = ["guestmount"]
    for binary in required_binaries:
        if not shutil.which(binary):
            print(f"Required binary '{binary}' is not installed, aborting.")
            sys.exit(1)


def main():
    check_environment()
    config = get_config()
    args, subparsers = parse_args(config)
    if args.command == "deploy":
        deploy(args, config, subparsers["deploy"])
    elif args.command == "image":
        manage_images(args, config, subparsers["image"])
    elif args.command == "ssh-keys":
        manage_ssh_keys(args, config, subparsers["ssh-keys"])


if __name__ == "__main__":
    main()
