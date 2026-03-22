from __future__ import annotations

import base64
import json
import shutil
import subprocess
import sys
from pathlib import Path

from rich.console import Console

console = Console()


class AnsibleRunner:
    def __init__(
        self,
        inventory_path: Path,
        playbooks_dir: Path | None = None,
    ) -> None:
        self.inventory_path = inventory_path
        self.playbooks_dir = playbooks_dir or Path(__file__).parent / "playbooks"

    @staticmethod
    def check_ansible_installed() -> None:
        if not shutil.which("ansible-playbook"):
            raise RuntimeError("ansible-playbook not found. Install it with: brew install ansible")

    def fetch_token(self) -> str:
        """Fetch k3s node token from control plane."""
        result = subprocess.run(
            [
                "ansible",
                "-i",
                str(self.inventory_path),
                "control_plane",
                "-m",
                "slurp",
                "-a",
                "src=/var/lib/rancher/k3s/server/node-token",
            ],
            capture_output=True,
            text=True,
        )

        # Find the JSON block after "SUCCESS =>"
        stdout = result.stdout
        if "SUCCESS =>" in stdout:
            json_str = stdout.split("SUCCESS =>")[1].strip()
            try:
                data = json.loads(json_str)
                return base64.b64decode(data["content"]).decode().strip()
            except Exception as e:
                raise RuntimeError(f"Failed to parse token response: {e}") from e

        raise RuntimeError("Failed to fetch k3s node token from control plane.")

    def run(
        self,
        playbook: str,
        extra_vars: dict[str, str] | None = None,
    ) -> int:
        self.check_ansible_installed()

        playbook_path = self.playbooks_dir / playbook

        if not playbook_path.exists():
            raise FileNotFoundError(f"Playbook not found: {playbook_path}")

        cmd = ["ansible-playbook", "-i", str(self.inventory_path), str(playbook_path), "-v"]

        if extra_vars:
            vars_str = " ".join(f"{key}={value}" for key, value in extra_vars.items())
            cmd += ["--extra-vars", vars_str]

        console.print(f"\n[bold]Running playbook:[/bold] [cyan]{playbook}[/cyan]")
        console.print(f"[dim]Playbook path: {playbook_path}[/dim]")
        console.print(f"[dim]Inventory path: {self.inventory_path}[/dim]")
        console.print(f"[dim]Command: {' '.join(cmd)}[/dim]")

        result = subprocess.run(
            cmd,
            check=False,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        return result.returncode
