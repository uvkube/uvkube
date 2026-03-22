import typer
from rich.console import Console

app = typer.Typer(
    name="uvkube",
    help="🚀 uvkube — Kubernetes infrastructure management for Hetzner Cloud",
    no_args_is_help=True,
)

console = Console()


@app.command()
def hello() -> None:
    """Say hello."""
    console.print("Hello from Mundo!", style="bold green")


if __name__ == "__main__":
    app()