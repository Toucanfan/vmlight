from pathlib import Path
from .utils import ApplicationError
from .utils import sh
from .xen import XenVmHelper
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
        self.image_dir = Path(self.config["general"]["image_dir"]).absolute()
        self.instances = self._get_instances()

    def _get_instances(self):
        """
        Get all VMs.
        """
        if not self.instances_dir.exists():
            return []
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

    def _get_vm_backend_helper(self, vm_id):
        vm = self.get_vm_by_id(vm_id)
        if vm.type == VmType.XEN:
            return XenVmHelper(vm, self.config)
        raise ApplicationError(f"Unsupported VM type: {vm.type}")

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

    def is_running(self, vm_id):
        """
        Check if an instance is running.
        """
        helper = self._get_vm_backend_helper(vm_id)
        return helper.is_running()

    def start_instance(self, vm_id):
        """
        Start an instance.
        """
        helper = self._get_vm_backend_helper(vm_id)
        return helper.start()

    def stop_instance(self, vm_id):
        """
        Stop an instance.
        """
        helper = self._get_vm_backend_helper(vm_id)
        return helper.stop()

    def restart_instance(self, vm_id):
        """
        Restart an instance.
        """
        helper = self._get_vm_backend_helper(vm_id)
        return helper.restart()

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
        helper = self._get_vm_backend_helper(vm_id)
        helper.delete()
