from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

@dataclass
class ServernNode:
  name: str
  ip: str
  status: str
  location: str
  server_type: str
  labels: dict[str, str]

class CloudProvider(Protocol):