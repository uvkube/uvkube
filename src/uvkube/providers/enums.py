from enum import StrEnum


class ServerStatus(StrEnum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    REBUILDING = "rebuilding"
    MIGRATING = "migrating"
    DELETING = "deleting"
    UNKNOWN = "unknown"
