from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from uvkube.config.models import (
    ClusterConfig,
    ControlPlaneConfig,
    Region,
    UvKubeConfig,
    WorkerNodeConfig,
)

load_dotenv()

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def init(
    name: Annotated[str, typer.Option("--name", "-n", help="Cluster name")] = "uvkube-cluster",
    region: Annotated[Region, typer.Option("--region", "-r", help="Cluster region")] = Region.NUREMBERG,
    workers: Annotated[int, typer.Option("--workers", "-w", help="Number of worker nodes")] = 3,
) -> None:
    """Initialize a new uvkube.yaml config file."""
    config_path = Path("uvkube.yaml")

    if config_path.exists():
        overwrite = typer.confirm("Config file already exists. Overwrite?", default=False)
        if not overwrite:
            console.print("Aborting.")
            raise typer.Abort()

    config = UvKubeConfig(
        clusters=[
            ClusterConfig(
                name=name,
                region=Region(region),
                control_plane=ControlPlaneConfig(),
                worker_nodes=WorkerNodeConfig(count=workers),
            )
        ]
    )

    config_path.write_text(config.to_yaml())

    console.print(
        Panel.fit(
            f"[green]✓[/green] Created [bold]uvkube.yaml[/bold]\n\n"
            f"  Cluster : [cyan]{name}[/cyan]\n"
            f"  Region  : [cyan]{region}[/cyan]\n"
            f"  Workers : [cyan]{workers}[/cyan]\n\n"
            f"Next step: [bold]uvkube infra up[/bold]",
            title="uvkube initialised",
            border_style="green",
        )
    )


@app.command()
def up(
    config_path: Annotated[Path, typer.Option("--config", "-c", help="Path to the config file")] = Path("uvkube.yaml"),
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-d", help="Show what would be done without actually doing it")
    ] = False,
) -> None:
    """Provision Hetzner servers for the Kubernetes cluster."""
    config = UvKubeConfig.from_file(config_path)

    from uvkube.providers.hetzner import HetznerProvider
    from uvkube.providers.in_memory import InMemoryCloudProvider

    provider = InMemoryCloudProvider() if dry_run else HetznerProvider()

    for cluster in config.clusters:
        console.print(f"\n[bold]Provisioning cluster:[/bold] [cyan]{cluster.name}[/cyan]")
        console.print(f"Region: [cyan]{cluster.region}[/cyan]\n")

        for i in range(cluster.control_plane.count):
            node_name = f"{cluster.name}-cp-{i + 1}"
            console.print(f"  [→] Control plane: [bold]{node_name}[/bold] ({cluster.control_plane.type})")
            server, created = provider.get_or_create_server(
                name=node_name,
                server_type=cluster.control_plane.type,
                location=cluster.region,
                labels={"uvkube-cluster": cluster.name, "uvkube-role": "control-plane"},
            )
            server_status: str = "[green]created[/green]" if created else "[yellow]already exists[/yellow]"
            console.print(f"      {server_status} — IP: [cyan]{server.ip}[/cyan]")

        for i in range(cluster.worker_nodes.count):
            node_name = f"{cluster.name}-worker-{i + 1}"
            console.print(f"  [→] Worker: [bold]{node_name}[/bold] ({cluster.worker_nodes.type})")
            server, created = provider.get_or_create_server(
                name=node_name,
                server_type=cluster.worker_nodes.type,
                location=cluster.region,
                labels={"uvkube-cluster": cluster.name, "uvkube-role": "worker"},
            )
            worker_status = "[green]created[/green]" if created else "[yellow]already exists[/yellow]"
            console.print(f"      {worker_status} — IP: [cyan]{server.ip}[/cyan]")

    console.print(
        Panel.fit(
            "[green]✓[/green] Infrastructure provisioned\n\nNext step: [bold]uvkube infra status[/bold]",
            border_style="green",
        )
    )


@app.command()
def status(
    config_path: Annotated[Path, typer.Option("--config", "-c", help="Path to the config file")] = Path("uvkube.yaml"),
) -> None:
    """Show the status of the Kubernetes cluster."""
    config = UvKubeConfig.from_file(config_path)

    from uvkube.providers.hetzner import HetznerProvider

    provider = HetznerProvider()

    for cluster in config.clusters:
        servers = provider.list_servers(label_selector=f"uvkube-cluster={cluster.name}")

        if not servers:
            console.print(f"[yellow]No servers found for cluster:[/yellow] {cluster.name}")
            continue

        table = Table(
            title=f"Cluster: {cluster.name}",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
        )

        table.add_column("Name", style="bold")
        table.add_column("Role")
        table.add_column("Type")
        table.add_column("IP")
        table.add_column("Status")
        table.add_column("Location")

        for server in servers:
            role = server.labels.get("uvkube-role", "unknown")
            role_color = "magenta" if role == "control-plane" else "blue"
            status_color = "green" if server.status == "running" else "yellow"

            table.add_row(
                server.name,
                f"[{role_color}]{role}[/{role_color}]",
                server.server_type,
                server.ip,
                f"[{status_color}]{server.status}[/{status_color}]",
                server.location,
            )

        console.print(table)


@app.command()
def destroy(
    config_path: Annotated[Path, typer.Option("--config", "-c", help="Path to the config file")] = Path("uvkube.yaml"),
    force: Annotated[bool, typer.Option("--force", "-f", help="Force destroy without confirmation")] = False,
) -> None:
    """Destroy the Kubernetes cluster."""
    config = UvKubeConfig.from_file(config_path)

    from uvkube.providers.hetzner import HetznerProvider

    provider = HetznerProvider()

    for cluster in config.clusters:
        if not force:
            confirm = typer.confirm(
                f"Delete All Servers for Cluster: [bold]{cluster.name}[/bold] (y/n)?", default=False
            )
            if not confirm:
                console.print("Aborting.")
                raise typer.Abort()

        servers = provider.list_servers(label_selector=f"uvkube-cluster={cluster.name}")

        if not servers:
            console.print(f"[yellow]No servers found for cluster:[/yellow] {cluster.name}")
            continue

        for server in servers:
            console.print(f"  [red]✗[/red] Deleting [bold]{server.name}[/bold]...")
            provider.delete_server(server.name)

        console.print(Panel.fit("[red]✓[/red] Cluster destroyed.", border_style="red"))
