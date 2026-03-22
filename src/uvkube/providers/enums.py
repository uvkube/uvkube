from enum import Enum

class ServerStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    REBUILDING = "rebuilding"
    MIGRATING = "migrating"
    DELETING = "deleting"
    UNKNOWN = "unknown"