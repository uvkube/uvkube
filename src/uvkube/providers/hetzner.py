from __future__ import annotations

import os
from typing import Optional

from hcloud import Client
from hcloud.images import Image
from hcloud.locations import Location
from hcloud.server_types import ServerType
from hcloud.servers import BoundServer, Server
from rich.console import Console

console = Console()

class HetznerProvider:
    def __init__(self, token: Optional[str] = None) -> None:
        api_token = token or os.getenv("HETZNER_API_TOKEN")
        if not api_token:
            raise ValueError("Hetzner API token is required. Set it via the HETZNER_API_TOKEN environment variable.")
        self.client = Client(token=api_token)

    def get_or_create_server(
            self,
            name: str,
            server_type: str,
            image: str = "ubuntu-22.04",
            labels: Optional[dict[str, str]] = None,
    ) -> tuple[Server, bool]:
        """Get existing server by name or create a new one if it doesn't exist."""
        existing_server = self.client.servers.get_by_name(name)
        if existing_server:
            console.print(f"Server '{name}' already exists. Reusing it.", style="yellow")
            return existing_server, False
        
        response = self.client.servers.create(
            name=name,
            server_type=ServerType(name=server_type),
            image=Image(name=image),
            labels=labels or {},
        )
        server = response.server
        console.print(f"Creating server '{name}' with type '{server_type}' and image '{image}'.", style="green")
        return server, True
  
    def list_serrvers(
          self,
          label_selector: Optional[str] = None,
    ) -> list[BoundServer]:
          """List servers, optionally filtering by label selector."""
          if label_selector:
              return self.client.servers.get_all(label_selector=label_selector)
          return self.client.servers.get_all()
    
    def delete_server(self, name: str) -> bool:
        """Delete server by name. Returns True if deleted, False if not found."""
        server = self.client.servers.get_by_name(name)
        if not server:
            console.print(f"Server '{name}' not found. Nothing to delete.", style="yellow")
            return False
        self.client.servers.delete(server)
        console.print(f"Deleted server '{name}'.", style="red")
        return True
    
    def get_server(self, name: str) -> Optional[BoundServer]:
        """Get server by name. Returns None if not found."""
        return self.client.servers.get_by_name(name)