from uvkube.providers.enums import ServerStatus
from uvkube.providers.in_memory import InMemoryCloudProvider


def test_creates_server_when_not_exists() -> None:
    provider = InMemoryCloudProvider()

    server, created = provider.get_or_create_server(
        name="test-server",
        server_type="cx22",
        location="nbg1",
    )

    assert created is True
    assert server.name == "test-server"
    assert server.status == ServerStatus.RUNNING

def test_returns_existing_server_without_creating() -> None:
    provider = InMemoryCloudProvider()
    provider.get_or_create_server(
        name="existing-server",
        server_type="cx22",
        location="nbg1",
    )
    server, created = provider.get_or_create_server(
        name="existing-server",
        server_type="cx22",
        location="nbg1",
    )

    assert created is False

def test_list_servers_returns_all_servers() -> None:
    provider = InMemoryCloudProvider()
    provider.get_or_create_server(
        name="test-cp-1",
        server_type="cx22",
        location="nbg1",
        labels={"role": "control-plane"},
    )
    provider.get_or_create_server(
        name="test-worker-1",
        server_type="cx22",
        location="nbg1",
        labels={"role": "worker"},
    )
    provider.get_or_create_server(
        name="test-worker-2",
        server_type="cx22",
        location="nbg1",
        labels={"role": "worker"},
    )

    servers = provider.list_servers()
    assert len(servers) == 3

def test_list_servers_filters_by_label() -> None:
    provider = InMemoryCloudProvider()
    provider.get_or_create_server(
        name="test-cp-1",
        server_type="cx22",
        location="nbg1",
        labels={"role": "control-plane"},
    )
    provider.get_or_create_server(
        name="test-worker-1",
        server_type="cx22",
        location="nbg1",
        labels={"role": "worker"},
    )

    servers = provider.list_servers(label_selector="role=control-plane")
    assert len(servers) == 1
    assert servers[0].name == "test-cp-1"

def test_delete_server_returns_false_when_not_found() -> None:
    provider = InMemoryCloudProvider()
    deleted = provider.delete_server("nonexistent-server")
    assert deleted is False