from .utils import ApplicationError
from argparse import ArgumentParser


def add_deploy_args(subparser: ArgumentParser, config):
    subparser.add_argument(
        "-i", "--interactive", action="store_true", help="Run in interactive mode"
    )
    subparser.add_argument("--name", help="Name of the instance")
    subparser.add_argument("--image", help="Name of the image")
    subparser.add_argument("--ip", help="IP address of the instance")
    subparser.add_argument(
        "--disk-size",
        default=config["deploy"]["disk_size"],
        help="Disk size of the instance",
    )
    subparser.add_argument(
        "--memory",
        default=config["deploy"]["memory"],
        help="Memory assigned to the instance",
    )
    subparser.add_argument(
        "--vcpus",
        default=config["deploy"]["vcpus"],
        help="Number of CPUs assigned to the instance",
    )
    subparser.add_argument(
        "--ssh-key", action="append", help="SSH key for the instance"
    )


def add_ssh_key_args(subparser: ArgumentParser, config):
    subparser.add_argument("--add", metavar="PUBKEY")
    subparser.add_argument("--add-file", metavar="FILE")
    subparser.add_argument("--remove", metavar="KEYNAME")
    subparser.add_argument("--list", action="store_true")


def add_image_args(subparser, config):
    subparser.add_argument("--add", metavar="IMAGE_FILE")
    subparser.add_argument("--remove", metavar="IMAGE_NAME")
    subparser.add_argument("--list", action="store_true")


def parse_args(config):
    """
    Parse the command line arguments.
    """
    parser = ArgumentParser(
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
    subparser_dict = {}

    # Custom usage for the deploy subparser
    deploy_parser = subparsers.add_parser(
        "deploy",
        help="Deploy a new instance",
        usage="%(prog)s [-h] [-i] [OPTIONS]",
    )
    add_deploy_args(deploy_parser, config)
    subparser_dict["deploy"] = deploy_parser

    ssh_key_parser = subparsers.add_parser("ssh-keys", help="Manage SSH keys")
    add_ssh_key_args(ssh_key_parser, config)
    subparser_dict["ssh-keys"] = ssh_key_parser

    image_parser = subparsers.add_parser("image", help="Manage OS images")
    add_image_args(image_parser, config)
    subparser_dict["image"] = image_parser

    return (parser.parse_args()), parser, subparser_dict
