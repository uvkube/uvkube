import typer
from rich.console import Console

from uvkube.commands import infra

app = typer.Typer(
    name="uvkube",
    help="🚀 uvkube — Kubernetes infrastructure management for Hetzner Cloud",
    no_args_is_help=True,
)

console = Console()

app.add_typer(infra.app, name="infra", help="Manage Hetzner Cloud infrastructure")


@app.callback()
def main() -> None:
    """uvkube: Kubernetes infrastructure management for Hetzner Cloud"""
    pass


if __name__ == "__main__":
    app()
