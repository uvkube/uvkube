from pathlib import Path

import pytest
import yaml

from uvkube.config.models import ClusterConfig, Region, UvKubeConfig


def test_default_region_is_nuremberg() -> None:
    cluster = ClusterConfig(name="test-cluster")
    assert cluster.region == Region.NUREMBERG

def test_invalid_region_raises_error() -> None:
    with pytest.raises(ValueError):
        ClusterConfig(name="test-cluster", region="invalid-region") # type: ignore


def test_config_from_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({
        "clusters": [
            {
                "name": "test-cluster",
                "region": "hel1",
                "k3s_version": "v1.32.0+k3s1",
                "control_plane": {"type": "cx22", "count": 1},
                "worker_nodes": {"type": "cx22", "count": 2},
            }
        ]
    }))

    config = UvKubeConfig.from_file(config_file)

    assert len(config.clusters) == 1
    assert config.clusters[0].name == "test-cluster"
    assert config.clusters[0].region == Region.HELSINKI
    assert config.clusters[0].k3s_version == "v1.32.0+k3s1"
    assert config.clusters[0].control_plane.type == "cx22"
    assert config.clusters[0].control_plane.count == 1
    assert config.clusters[0].worker_nodes.type == "cx22"
    assert config.clusters[0].worker_nodes.count == 2


def test_config_from_nonexistent_file_raises_error(tmp_path: Path) -> None:
    non_existent_file = tmp_path / "nonexistent.yaml"
    with pytest.raises(FileNotFoundError):
        UvKubeConfig.from_file(non_existent_file)