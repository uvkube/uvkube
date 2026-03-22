from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class Region(StrEnum):
    NUREMBERG = "nbg1"
    FALKENSTEIN = "fsn1"
    HELSINKI = "hel1"
    ASHBURN = "ash"
    HILLSBORO = "hil"


class ControlPlaneConfig(BaseModel):
    type: str = "cx22"
    count: int = 1


class WorkerNodeConfig(BaseModel):
    type: str = "cx22"
    count: int = 2


class ClusterConfig(BaseModel):
    name: str
    region: Region = Region.NUREMBERG
    k3s_version: str = "v1.32.0+k3s1"
    control_plane: ControlPlaneConfig = Field(default_factory=ControlPlaneConfig)
    worker_nodes: WorkerNodeConfig = Field(default_factory=WorkerNodeConfig)


class UvKubeConfig(BaseModel):
    clusters: list[ClusterConfig] = Field(default_factory=list)

    @classmethod
    def from_file(cls, file_path: Path) -> UvKubeConfig:
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        with file_path.open() as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_yaml(self) -> str:
        result = yaml.dump(
            self.model_dump(mode="json"),
            default_flow_style=False,
            sort_keys=False,
        )
        return str(result)
