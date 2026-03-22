from uvkube.ansible.inventory import AnsibleInventory
from uvkube.providers.base import ServerNode
from uvkube.providers.enums import ServerStatus


def make_node(name: str, ip: str) -> ServerNode:
    return ServerNode(
        name=name,
        ip=ip,
        status=ServerStatus.RUNNING,
        location="nbg1",
        server_type="cx23",
        labels={},
    )


def test_inventory_renders_control_plane() -> None:
    inventory = AnsibleInventory(
        control_plane_nodes=[make_node("test-cp-1", "192.168.1.100")],
        worker_nodes=[],
    )

    result = inventory.render()

    assert "[control_plane]" in result
    assert "test-cp-1 ansible_host=192.168.1.100" in result


def test_inventory_renders_worker_nodes() -> None:
    inventory = AnsibleInventory(
        control_plane_nodes=[],
        worker_nodes=[make_node("test-worker-1", "192.168.2.100")],
    )

    result = inventory.render()

    assert "[workers]" in result
    assert "test-worker-1 ansible_host=192.168.2.100" in result


def test_inventory_renders_k3s_children_group() -> None:
    inventory = AnsibleInventory(
        control_plane_nodes=[make_node("test-cp-1", "10.0.0.1")],
        worker_nodes=[make_node("test-worker-1", "10.0.0.2")],
    )

    result = inventory.render()

    assert "[k3s:children]" in result
    assert "[control_plane]" in result
    assert "[workers]" in result


def test_inventory_write(tmp_path) -> None:
    inventory = AnsibleInventory(
        control_plane_nodes=[make_node("test-cp-1", "10.0.0.1")],
        worker_nodes=[make_node("test-worker-1", "10.0.0.2")],
    )
    path = tmp_path / "inventory.yaml"
    inventory.write(path)

    assert path.exists()
    assert "test-cp-1 ansible_host=10.0.0.1" in path.read_text()
