from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv
from hcloud import APIException
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
from uvkube.providers.base import ServerNode

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
    bootstrap: Annotated[bool, typer.Option("--bootstrap", "-b", help="Bootstrap k3s after provisioning")] = False,
    ssh_key: Annotated[str, typer.Option("--ssh-key", help="Path to SSH private key")] = "~/.ssh/id_rsa",
) -> None:
    """Provision Hetzner servers for the cluster."""
    config = UvKubeConfig.from_file(config_path)

    from uvkube.providers.hetzner import HetznerProvider
    from uvkube.providers.in_memory import InMemoryCloudProvider

    provider = InMemoryCloudProvider() if dry_run else HetznerProvider()

    for cluster in config.clusters:
        console.print(f"\n[bold]Provisioning cluster:[/bold] [cyan]{cluster.name}[/cyan]")
        console.print(f"Region: [cyan]{cluster.region}[/cyan]\n")

        control_plane_nodes = []
        worker_nodes = []

        for i in range(cluster.control_plane.count):
            node_name = f"{cluster.name}-cp-{i + 1}"
            console.print(f"  [→] Control plane: [bold]{node_name}[/bold] ({cluster.control_plane.type})")
            server, created = provider.get_or_create_server(
                name=node_name,
                server_type=cluster.control_plane.type,
                location=cluster.region,
                labels={"uvkube-cluster": cluster.name, "uvkube-role": "control-plane"},
                ssh_key_name=cluster.ssh_key_name,
            )
            server_status = "[green]created[/green]" if created else "[yellow]already exists[/yellow]"
            console.print(f"      {server_status} — IP: [cyan]{server.ip}[/cyan]")
            control_plane_nodes.append(server)

        for i in range(cluster.worker_nodes.count):
            node_name = f"{cluster.name}-worker-{i + 1}"
            console.print(f"  [→] Worker: [bold]{node_name}[/bold] ({cluster.worker_nodes.type})")
            server, created = provider.get_or_create_server(
                name=node_name,
                server_type=cluster.worker_nodes.type,
                location=cluster.region,
                labels={"uvkube-cluster": cluster.name, "uvkube-role": "worker"},
                ssh_key_name=cluster.ssh_key_name,
            )
            server_status = "[green]created[/green]" if created else "[yellow]already exists[/yellow]"
            console.print(f"      {server_status} — IP: [cyan]{server.ip}[/cyan]")
            worker_nodes.append(server)

        if bootstrap and not dry_run:
            _run_bootstrap(cluster.name, cluster.k3s_version, control_plane_nodes, worker_nodes, ssh_key)

    console.print(
        Panel.fit(
            "[green]✓[/green] Infrastructure provisioned\n\nNext step: [bold]uvkube infra bootstrap[/bold]",
            border_style="green",
        )
    )


@app.command()
def bootstrap(
    config_path: Annotated[Path, typer.Option("--config", "-c", help="Path to the config file")] = Path("uvkube.yaml"),
    ssh_key: Annotated[str, typer.Option("--ssh-key", help="Path to SSH private key")] = "~/.ssh/id_rsa",
) -> None:
    """Bootstrap k3s on existing cluster servers."""
    config = UvKubeConfig.from_file(config_path)

    from uvkube.providers.hetzner import HetznerProvider

    provider = HetznerProvider()

    for cluster in config.clusters:
        control_plane_nodes = provider.list_servers(
            label_selector=f"uvkube-cluster={cluster.name},uvkube-role=control-plane"
        )
        worker_nodes = provider.list_servers(label_selector=f"uvkube-cluster={cluster.name},uvkube-role=worker")

        if not control_plane_nodes:
            console.print(f"[red]✗[/red] No servers found for cluster: {cluster.name}")
            console.print("Run [bold]uvkube infra up[/bold] first.")
            raise typer.Exit(code=1)

        _run_bootstrap(cluster.name, cluster.k3s_version, control_plane_nodes, worker_nodes, ssh_key)


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


@app.command()
def server_types() -> None:
    """List available server types."""
    from uvkube.providers.hetzner import HetznerProvider

    provider = HetznerProvider()
    types = provider.client.server_types.get_all()
    for t in types:
        console.print(f"[cyan]{t.name}[/cyan] — {t.description} — cores: {t.cores} ram: {t.memory}GB")


@app.command()
def ssh_key_add(
    name: Annotated[str, typer.Option("--name", "-n", help="Name for the SSH key")],
    public_key: Annotated[
        str, typer.Option("--public-key", "-k", help="Path to public key file")
    ] = "~/.ssh/id_rsa.pub",
) -> None:
    """Upload an SSH public key to Hetzner Cloud."""
    from uvkube.providers.hetzner import HetznerProvider

    key_path = Path(public_key).expanduser()

    if not key_path.exists():
        console.print(f"[red]✗[/red] Public key not found: {key_path}")
        raise typer.Exit(code=1)

    provider = HetznerProvider()

    existing = provider.client.ssh_keys.get_by_name(name)
    if existing:
        console.print(f"[yellow]SSH key '{name}' already exists in Hetzner.[/yellow]")
        raise typer.Exit()

    try:
        provider.client.ssh_keys.create(
            name=name,
            public_key=key_path.read_text().strip(),
        )
    except APIException as e:
        if "not unique" in str(e):
            console.print(
                "[yellow]This public key already exists in Hetzner under a different name.[/yellow]\n"
                "Run [bold]uvkube infra ssh-key-list[/bold] to see existing keys."
            )
            raise typer.Exit(code=1)
        raise

    console.print(
        Panel.fit(
            f"[green]✓[/green] SSH key [bold]{name}[/bold] uploaded to Hetzner\n\n"
            f"Use it with: [bold]uvkube infra up --ssh-key-name {name}[/bold]",
            border_style="green",
        )
    )


@app.command()
def ssh_key_list() -> None:
    """List SSH keys in Hetzner Cloud."""
    from uvkube.providers.hetzner import HetznerProvider

    provider = HetznerProvider()
    keys = provider.client.ssh_keys.get_all()

    if not keys:
        console.print("[yellow]No SSH keys found.[/yellow]")
        raise typer.Exit()

    table = Table(box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Name", style="bold")
    table.add_column("Fingerprint")

    for key in keys:
        table.add_row(key.name, key.fingerprint)

    console.print(table)

@app.command()
def firewall(
    config_path: Annotated[
        Path, typer.Option("--config", "-c", help="Path to the config file")
    ] = Path("uvkube.yaml"),
) -> None:
    """Create and apply Hetzner firewall rules for the cluster."""
    from uvkube.providers.hetzner import HetznerProvider

    config = UvKubeConfig.from_file(config_path)
    provider = HetznerProvider()

    for cluster in config.clusters:
        created = provider.create_cluster_firewall(cluster.name)
        if created:
            console.print(f"[green]✓[/green] Firewall created and applied to [bold]{cluster.name}[/bold]")
        else:
            console.print(f"[yellow]Firewall already exists for cluster:[/yellow] {cluster.name}")

def _run_bootstrap(
    cluster_name: str,
    k3s_version: str,
    control_plane_nodes: list[ServerNode],
    worker_nodes: list[ServerNode],
    ssh_key: str,
) -> None:
    from uvkube.ansible.inventory import AnsibleInventory
    from uvkube.ansible.runner import AnsibleRunner

    inventory_path = Path(f".uvkube/{cluster_name}/inventory.ini")
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    kubeconfig_path = Path(f".uvkube/{cluster_name}/kubeconfig.yaml").resolve()

    inventory = AnsibleInventory(
        control_plane_nodes=control_plane_nodes,
        worker_nodes=worker_nodes,
        ssh_private_key=ssh_key,
    )
    inventory.write(inventory_path)
    console.print(f"\n[green]✓[/green] Inventory written to [cyan]{inventory_path}[/cyan]")

    runner = AnsibleRunner(inventory_path=inventory_path)

    console.print("\n[bold]Bootstrapping k3s control plane...[/bold]")
    rc = runner.run(
        "k3s_control_plane.yml",
        extra_vars={
            "k3s_version": k3s_version,
            "kubeconfig_path": str(kubeconfig_path),
        },
    )
    if rc != 0:
        console.print("[red]✗[/red] Control plane bootstrap failed.")
        raise typer.Exit(code=1)

    console.print("\n[bold]Bootstrapping k3s workers...[/bold]")
    token = runner.fetch_token()
    console.print("[green]✓[/green] Node token fetched.")
    rc = runner.run(
        "k3s_workers.yml",
        extra_vars={
            "k3s_version": k3s_version,
            "control_plane_ip": control_plane_nodes[0].ip,
            "k3s_token": token,
        },
    )
    if rc != 0:
        console.print("[red]✗[/red] Worker bootstrap failed.")
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            "[green]✓[/green] Cluster is ready\n\n"
            f"Kubeconfig: [cyan].uvkube/{cluster_name}/kubeconfig.yaml[/cyan]\n\n"
            f"Next: [bold]export KUBECONFIG=.uvkube/{cluster_name}/kubeconfig.yaml[/bold]",
            border_style="green",
        )
    )
