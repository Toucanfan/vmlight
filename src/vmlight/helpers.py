class VmBackendHelper:
    def __init__(self, vm, config):
        self.vm = vm
        self.config = config

    def is_running(self):
        raise NotImplementedError

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def restart(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError
