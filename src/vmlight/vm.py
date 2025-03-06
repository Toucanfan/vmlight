from pathlib import Path
from .utils import ApplicationError
from .utils import sh
import subprocess
from enum import Enum


class VmType(Enum):
    XEN = "xen"
    KVM = "kvm"
    SYSTEMD_NSPAWN = "systemd-nspawn"
    UNKNOWN = "unknown"


class Vm:
    def __init__(self, vm_id, vm_name, vm_type):
        self.id = vm_id
        self.name = vm_name
        self.type = vm_type


class VmManager:
    def __init__(self, config):
        self.config = config
        self.instances_dir = Path(self.config["general"]["instances_dir"]).absolute()
        self.instances_dir.mkdir(parents=True, exist_ok=True)
        self.image_dir = Path(self.config["general"]["image_dir"]).absolute()
        self.instances = self._get_instances()
        self.xl_path = Path(self.config["xen"]["xl_path"]).absolute()

    def _get_instances(self):
        """
        Get all VMs.
        """
        instances = [i.name for i in self.instances_dir.glob("*")]
        instances.sort()
        vms = []
        for i in instances:
            vm_id, vm_name = i.split("-")
            vm_type = self._get_vm_type(i)
            vms.append(Vm(vm_id, vm_name, vm_type))
        return vms

    def _get_vm_type(self, instance_dir_name):
        if Path(self.instances_dir / instance_dir_name / "xen_vm.cfg").exists():
            return VmType.XEN
        return VmType.UNKNOWN

    def list_instances(self):
        """
        List all instances.
        """
        print(f"{'ID':<6} {'NAME':<40} {'TYPE':<10} {'STATUS'}")
        for vm in self.instances:
            status = (
                "\033[1;32mRunning\033[0m"
                if self.is_running(vm.id)
                else "\033[1;31mStopped\033[0m"
            )
            print(f"{vm.id:<6} {vm.name:<40} {vm.type.value:<10} {status}")

    def get_vm_by_id(self, vm_id) -> Vm:
        """
        Get a VM by ID.
        """
        for vm in self.instances:
            if vm.id == vm_id:
                return vm
        raise ApplicationError(f"VM with ID {vm_id} not found")

    def get_xen_domain_id(self, vm_id):
        """
        Get the domain ID of a Xen VM.
        """
        vm = self.get_vm_by_id(vm_id)
        if vm.type != VmType.XEN:
            raise ApplicationError(f"VM with ID {vm_id} is not a Xen VM")
        try:
            result = sh(f"{self.xl_path} list")
            lines = result.splitlines()
            for line in lines[1:]:  # Skip the header line
                columns = line.split()
                name = columns[0]
                domain_id = columns[1]
                if name.startswith(f"{vm_id}-"):
                    return domain_id
            raise ApplicationError(f"A running Xen VM with ID {vm_id} not found")
        except subprocess.CalledProcessError as e:
            raise ApplicationError(f"Error executing 'xl list': {e}") from e

    def is_running(self, vm_id):
        """
        Check if an instance is running.
        """
        vm = self.get_vm_by_id(vm_id)
        if vm.type == VmType.XEN:
            try:
                result = sh(f"{self.xl_path} list")
                lines = result.splitlines()
                for line in lines[1:]:  # Skip the header line
                    columns = line.split()
                    name = columns[0]
                    state = columns[4]
                    if name.startswith(f"{vm_id}-") and any(
                        l in state for l in ["r", "b"]
                    ):
                        return True
                return False
            except subprocess.CalledProcessError as e:
                raise ApplicationError(f"Error executing 'xl list': {e}") from e
        else:
            raise ApplicationError(f"Unsupported VM type: {vm.type}")

    def start_instance(self, vm_id):
        """
        Start an instance.
        """
        vm = self.get_vm_by_id(vm_id)
        if vm.type == VmType.XEN:
            try:
                sh(
                    f"{self.xl_path} create {self.instances_dir / f'{vm_id}-{vm.name}' / 'xen_vm.cfg'}"
                )
                return True
            except ApplicationError as e:
                raise ApplicationError(f"Error starting Xen VM: {e}") from e
        else:
            raise ApplicationError(f"Unsupported VM type: {vm.type}")

    def stop_instance(self, vm_id):
        """
        Stop an instance.
        """
        vm = self.get_vm_by_id(vm_id)
        if vm.type == VmType.XEN:
            try:
                domain_id = self.get_xen_domain_id(vm_id)
                sh(f"{self.xl_path} shutdown {domain_id}")
                return True
            except ApplicationError as e:
                raise ApplicationError(f"Error stopping Xen VM: {e}") from e
        else:
            raise ApplicationError(f"Unsupported VM type: {vm.type}")

    def restart_instance(self, vm_id):
        """
        Restart an instance.
        """
        vm = self.get_vm_by_id(vm_id)
        if vm.type == VmType.XEN:
            try:
                domain_id = self.get_xen_domain_id(vm_id)
                sh(f"{self.xl_path} reboot {domain_id}")
                return True
            except ApplicationError as e:
                raise ApplicationError(f"Error restarting Xen VM: {e}") from e
        else:
            raise ApplicationError(f"Unsupported VM type: {vm.type}")

    def delete_instance(self, vm_id):
        """
        Delete an instance.
        """
        vm = self.get_vm_by_id(vm_id)
        if self.is_running(vm_id):
            raise ApplicationError(f"VM with ID {vm_id} is running")
        print(f"You are about to delete the instance '{vm.id}-{vm.name}'.")
        print(f"This action cannot be undone.")
        confirmation = input(
            "Are you sure you want to delete this instance? Type 'YES, I am sure!' to confirm: "
        )
        if confirmation != "YES, I am sure!":
            raise ApplicationError("Instance deletion aborted by user.")
        sh(f"rm -rf {self.instances_dir / f'{vm_id}-{vm.name}'}")
        if vm.type == VmType.XEN:
            auto_dir = Path(self.config["xen"]["conf_dir"]) / "auto"
            sh(f"rm -f {auto_dir / f'{vm_id}-{vm.name}'}")
