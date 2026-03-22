from __future__ import annotations

import os

from hcloud import Client
from hcloud.firewalls import FirewallResource, FirewallRule
from hcloud.images import Image
from hcloud.locations import Location
from hcloud.server_types import ServerType
from hcloud.servers import BoundServer
from hcloud.ssh_keys import SSHKey
from rich.console import Console

from uvkube.providers.base import ServerNode
from uvkube.providers.enums import ServerStatus

console = Console()


class HetznerProvider:
    def __init__(self, token: str | None = None) -> None:
        api_token = token or os.getenv("HETZNER_API_TOKEN")
        if not api_token:
            raise ValueError("Hetzner API token is required. Set it via the HETZNER_API_TOKEN environment variable.")
        self.client = Client(token=api_token)

    @staticmethod
    def _to_server_node(server: BoundServer) -> ServerNode:
        public_net = server.public_net
        ip = public_net.ipv4.ip if public_net and public_net.ipv4 else ""
        location = server.location.name if server.location else ""
        server_type = server.server_type.name if server.server_type else ""

        try:
            status = ServerStatus(server.status)
        except ValueError:
            status = ServerStatus.UNKNOWN

        return ServerNode(
            name=server.name,
            ip=ip,
            status=status,
            location=location,
            server_type=server_type,
            labels=server.labels,
        )

    def get_or_create_server(
        self,
        name: str,
        server_type: str,
        location: str,
        image: str = "ubuntu-22.04",
        labels: dict[str, str] | None = None,
        ssh_key_name: str | None = None,
    ) -> tuple[ServerNode, bool]:
        """Get an existing server by name or create a new one if it doesn't exist."""
        existing_server = self.client.servers.get_by_name(name)
        if existing_server:
            console.print(f"Server '{name}' already exists. Reusing it.", style="yellow")
            return self._to_server_node(existing_server), False

        ssh_keys = []
        if ssh_key_name:
            ssh_keys = [SSHKey(name=ssh_key_name)]

        response = self.client.servers.create(
            name=name,
            server_type=ServerType(name=server_type),
            image=Image(name=image),
            location=Location(name=location),
            labels=labels or {},
            ssh_keys=ssh_keys,
        )
        server = response.server
        console.print(
            f"Creating server '{name}' with type '{server_type}' and image '{image}'.",
            style="green",
        )
        return self._to_server_node(server), True

    def list_servers(
        self,
        label_selector: str | None = None,
    ) -> list[ServerNode]:
        """List servers, optionally filtering by label selector."""
        servers = self.client.servers.get_all(label_selector=label_selector)
        return [self._to_server_node(server) for server in servers]

    def delete_server(self, name: str) -> bool:
        """Delete server by name. Returns True if deleted, False if not found."""
        server = self.client.servers.get_by_name(name)
        if not server:
            console.print(f"Server '{name}' not found. Nothing to delete.", style="yellow")
            return False
        self.client.servers.delete(server)
        console.print(f"Deleted server '{name}'.", style="red")
        return True

    def get_server(self, name: str) -> ServerNode | None:
        """Get server by name. Returns None if not found."""
        server = self.client.servers.get_by_name(name)
        if not server:
            return None
        return self._to_server_node(server)

    def create_cluster_firewall(self, cluster_name: str) -> bool:
        """Create and apply firewall for cluster. Returns True if created, False if exists."""
        firewall_name = f"{cluster_name}-firewall"

        existing = self.client.firewalls.get_by_name(firewall_name)
        if existing:
            return False

        firewall = self.client.firewalls.create(
            name=firewall_name,
            rules=[
                FirewallRule(direction="in", protocol="tcp", port="22", source_ips=["0.0.0.0/0", "::/0"]),
                FirewallRule(direction="in", protocol="tcp", port="6443", source_ips=["0.0.0.0/0", "::/0"]),
                FirewallRule(direction="in", protocol="tcp", port="30000-32767", source_ips=["0.0.0.0/0", "::/0"]),
            ],
        ).firewall

        servers = self.list_servers(label_selector=f"uvkube-cluster={cluster_name}")
        for server in servers:
            hcloud_server = self.client.servers.get_by_name(server.name)
            self.client.firewalls.apply_to_resources(
                firewall,
                [FirewallResource(type="server", server=hcloud_server)],
            )

        return True
