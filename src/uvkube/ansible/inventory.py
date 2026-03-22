from __future__ import annotations

from pathlib import Path

from uvkube.providers.base import ServerNode


class AnsibleInventory:
    def __init__(
        self,
        control_plane_nodes: list[ServerNode],
        worker_nodes: list[ServerNode],
        ssh_user: str = "root",
        ssh_private_key: str = "~/.ssh/id_rsa",
    ) -> None:
        self.control_plane_nodes = control_plane_nodes
        self.worker_nodes = worker_nodes
        self.ssh_user = ssh_user
        self.ssh_private_key = ssh_private_key

    def render(self) -> str:
        lines: list[str] = ["[control_plane]"]
        for node in self.control_plane_nodes:
            lines.append(
                f"{node.name} ansible_host={node.ip} "
                f"ansible_user={self.ssh_user} "
                f"ansible_ssh_private_key_file={self.ssh_private_key}"
            )
        lines.append("")
        lines.append("[workers]")
        for node in self.worker_nodes:
            lines.append(
                f"{node.name} ansible_host={node.ip} "
                f"ansible_user={self.ssh_user} "
                f"ansible_ssh_private_key_file={self.ssh_private_key}"
            )
        lines.append("")

        lines.append("")
        lines.append("[k3s:children]")
        lines.append("control_plane")
        lines.append("workers")

        return "\n".join(lines)

    def write(self, path: Path) -> None:
        path.write_text(self.render())
        print(f"Inventory written to {path}")
