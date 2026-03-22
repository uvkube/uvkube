from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from uvkube.providers.enums import ServerStatus


@dataclass
class ServerNode:
  name: str
  ip: str
  status: ServerStatus
  location: str
  server_type: str
  labels: dict[str, str]

class CloudProvider(Protocol):
  def get_or_create_server(
          self,
          name: str,
          server_type: str,
          image: str = "ubuntu-22.04",
          labels: Optional[dict[str, str]] = None,
  ) -> tuple[ServerNode, bool]:
      """Get an existing server by name or create a new one if it doesn't exist."""
      ...

  def list_servers(
        self,
        label_selector: Optional[str] = None,
  ) -> list[ServerNode]:
        """List servers, optionally filtering by label selector."""
        ...

  def delete_server(self, name: str) -> bool:
      """Delete server by name. Returns True if deleted, False if not found."""
      ...

  def get_server(self, name: str) -> Optional[ServerNode]:
      """Get server by name. Returns ServerNode if found, None if not found."""
      ...