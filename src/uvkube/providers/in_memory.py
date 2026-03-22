from uvkube.providers.base import ServerNode
from uvkube.providers.enums import ServerStatus


class InMemoryCloudProvider:
    def __init__(self) -> None:
        self._servers: dict[str, ServerNode] = {}

    def get_or_create_server(
        self,
        name: str,
        server_type: str,
        location: str,
        image: str = "ubuntu-22.04",
        labels: dict[str, str] | None = None,
    ) -> tuple[ServerNode, bool]:
        if name in self._servers:
            return self._servers[name], False

        server = ServerNode(
            name=name,
            ip=f"10.0.0.{len(self._servers) + 1}",
            status=ServerStatus.RUNNING,
            location=location,
            server_type=server_type,
            labels=labels or {},
        )
        self._servers[name] = server
        return server, True

    def list_servers(self, label_selector: str | None = None) -> list[ServerNode]:
        if not label_selector:
            return list(self._servers.values())

        key, value = label_selector.split("=")
        return [
            server
            for server in self._servers.values()
            if server.labels.get(key) == value
        ]

    def delete_server(self, name: str) -> bool:
        if name not in self._servers:
            return False
        del self._servers[name]
        return True

    def get_server(self, name: str) -> ServerNode | None:
        return self._servers.get(name)
