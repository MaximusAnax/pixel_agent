"""Attach OSWorld's ``DesktopEnv`` to an already-running VM.

OSWorld's built-in providers all *start* a VM (Docker container, cloud instance,
VMware). On Babel we boot the VM ourselves under Apptainer+QEMU (see
``scripts/launch_vm.sh``) and just need ``DesktopEnv`` to talk to the guest HTTP
server that is already up. This module provides a no-op "manual" provider/manager
and an ``install()`` that monkeypatches OSWorld's factory so
``DesktopEnv(provider_name="docker", ...)`` uses it.

We keep ``provider_name="docker"`` because ``DesktopEnv.__init__`` only accepts a
fixed set of names, and "docker" gives the semantics we want: the environment is
treated as clean (``is_environment_used = False``), so ``reset()`` runs task
setup without trying to revert a snapshot.

Usage:
    from osworld_manual_provider import install
    install(host="127.0.0.1", server_port=5000, chromium_port=9222,
            vnc_port=8006, vlc_port=8080)
    env = DesktopEnv(provider_name="docker", action_space="pyautogui",
                     require_a11y_tree=False)
"""
from __future__ import annotations

import os

from desktop_env.providers.base import Provider, VMManager


class ManualProvider(Provider):
    """No-op provider for a VM whose lifecycle we manage outside OSWorld."""

    def __init__(self, region: str = None):
        super().__init__(region)
        self.host = os.environ.get("OSWORLD_VM_HOST", "127.0.0.1")
        self.server_port = int(os.environ.get("OSWORLD_SRV_PORT", "5000"))
        self.chromium_port = int(os.environ.get("OSWORLD_CDP_PORT", "9222"))
        self.vnc_port = int(os.environ.get("OSWORLD_VNC_PORT", "8006"))
        self.vlc_port = int(os.environ.get("OSWORLD_VLC_PORT", "8080"))

    def start_emulator(self, path_to_vm=None, headless=True, os_type="Ubuntu", *a, **k):
        return  # already running

    def get_ip_address(self, path_to_vm=None) -> str:
        return f"{self.host}:{self.server_port}:{self.chromium_port}:{self.vnc_port}:{self.vlc_port}"

    def save_state(self, path_to_vm, snapshot_name):
        raise NotImplementedError("Snapshots are not available for the manual provider")

    def revert_to_snapshot(self, path_to_vm, snapshot_name):
        return path_to_vm  # no-op; lifecycle handled by launch_vm.sh

    def stop_emulator(self, path_to_vm=None, *a, **k):
        return  # teardown handled externally


class ManualVMManager(VMManager):
    def __init__(self, registry_path: str = ""):
        pass

    def initialize_registry(self, **kwargs):
        pass

    def add_vm(self, vm_path, **kwargs):
        pass

    def delete_vm(self, vm_path, **kwargs):
        pass

    def occupy_vm(self, vm_path, pid, **kwargs):
        pass

    def list_free_vms(self, **kwargs):
        return ["manual-vm"]

    def check_and_clean(self, **kwargs):
        pass

    def get_vm_path(self, os_type="Ubuntu", region=None, screen_size=(1920, 1080), **kwargs):
        return "manual-vm"


def install(host: str = None, server_port: int = None, chromium_port: int = None,
            vnc_port: int = None, vlc_port: int = None):
    """Monkeypatch OSWorld's factory so DesktopEnv attaches to our running VM."""
    if host is not None:
        os.environ["OSWORLD_VM_HOST"] = str(host)
    if server_port is not None:
        os.environ["OSWORLD_SRV_PORT"] = str(server_port)
    if chromium_port is not None:
        os.environ["OSWORLD_CDP_PORT"] = str(chromium_port)
    if vnc_port is not None:
        os.environ["OSWORLD_VNC_PORT"] = str(vnc_port)
    if vlc_port is not None:
        os.environ["OSWORLD_VLC_PORT"] = str(vlc_port)

    import desktop_env.desktop_env as de

    def _factory(provider_name, region, use_proxy=False):
        return ManualVMManager(), ManualProvider(region)

    de.create_vm_manager_and_provider = _factory
