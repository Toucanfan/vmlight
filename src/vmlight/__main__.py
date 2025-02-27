import argparse
import configparser
import os
import sys
import shutil

from xen import XenDeployAgent


def get_config():
    """
    Get configuration from INI file or defaults.
    Returns a dictionary with configuration values.
    """
    config_dict = {
        "general": {
            "image_dir": "/var/lib/vmm/images",
            "instances_dir": "/var/lib/vmm/instances",
        },
        "deploy": {
            "memory": "512",
            "disk_size": "10G",
            "vcpus": "1",
            "type": "xen",
            "ssh_key_list_file": "/etc/vmm/ssh_key_store",
            "default_gateway": "10.10.10.2",
        },
        "xen": {
            "conf_dir": "/etc/xen",
            "pvgrub_path": "/usr/lib/xen/bin/pvgrub",
        },
    }

    config_files = [
        os.path.expanduser("~/.config/vmm.conf"),  # Local user config
        "/etc/vmm/vmm.conf",  # Global system config
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


def parse_args(config):
    """
    Parse the command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="""
        This program is used as a unified manager of Xen, KVM
        and systemd-nspawn instances.
        It is used mainly for deployment and configuration,
        but also supports basic monitoring and management."""
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1")
    parser.add_argument(
        "-t", "--type", default=config["deploy"]["type"], help="Type of the instance"
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Commands")
    deploy_parser = subparsers.add_parser("deploy", help="Deploy a new instance")
    deploy_parser.add_argument(
        "-i", "--interactive", action="store_true", help="Run in interactive mode"
    )
    deploy_parser.add_argument("--name", required=True, help="Name of the instance")
    deploy_parser.add_argument("--image", required=True, help="Name of the image")
    deploy_parser.add_argument("--ip", required=True, help="IP address of the instance")
    deploy_parser.add_argument(
        "--disk-size",
        default=config["deploy"]["disk_size"],
        help="Disk size of the instance",
    )
    deploy_parser.add_argument(
        "--memory",
        default=config["deploy"]["memory"],
        help="Memory assigned to the instance",
    )
    deploy_parser.add_argument(
        "--vcpus",
        default=config["deploy"]["vcpus"],
        help="Number of CPUs assigned to the instance",
    )
    deploy_parser.add_argument(
        "--ssh-key", action="append", help="SSH key for the instance"
    )
    list_images_parser = subparsers.add_parser(
        "list-images", help="List available images"
    )
    return parser.parse_args()


def deploy(args, config):
    if args.type == "xen":
        agent = XenDeployAgent(args, config)
        agent.deploy()

    elif args.type == "kvm":
        print("Deploying a KVM instance")
    elif args.type == "systemd-nspawn":
        print("Deploying a systemd-nspawn instance")


def list_images(config):
    print("Listing available images")


def require_root():
    if os.geteuid() != 0:
        print("Not running as root, aborting.")
        sys.exit(1)


def check_environment():
    required_binaries = ["guestmount"]
    for binary in required_binaries:
        if not shutil.which(binary):
            print(f"Required binary '{binary}' is not installed, aborting.")
            sys.exit(1)


if __name__ == "__main__":
    check_environment()
    config = get_config()
    args = parse_args(config)
    if args.command == "deploy":
        require_root()
        deploy(args, config)
    elif args.command == "list-images":
        list_images(config)
