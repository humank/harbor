"""Harbor CLI — command-line interface for agent management."""

import sys
from typing import Any

import click
import httpx

DEFAULT_BASE = "http://localhost:8100/api/v1"


class HarborClient:
    """Thin HTTP client for Harbor API."""

    def __init__(self, base_url: str, token: str = "") -> None:
        self.base = base_url.rstrip("/")
        self.headers: dict[str, str] = {"Content-Type": "application/json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        resp = httpx.request(
            method, f"{self.base}{path}", headers=self.headers, timeout=10, **kwargs
        )
        if resp.status_code >= 400:
            click.secho(f"Error {resp.status_code}: {resp.text}", fg="red", err=True)
            sys.exit(1)
        return resp.json() if resp.text else None

    def get(self, path: str) -> Any:
        return self._request("GET", path)

    def post(self, path: str, data: Any = None) -> Any:
        return self._request("POST", path, json=data)

    def put(self, path: str) -> Any:
        return self._request("PUT", path)

    def delete(self, path: str) -> Any:
        return self._request("DELETE", path)


@click.group()
@click.option("--url", envvar="HARBOR_URL", default=DEFAULT_BASE, help="Harbor API base URL")
@click.option("--token", envvar="HARBOR_TOKEN", default="", help="Bearer token")
@click.pass_context
def cli(ctx: click.Context, url: str, token: str) -> None:
    """⚓ Harbor — Agent Platform Management CLI."""
    ctx.ensure_object(dict)
    ctx.obj["client"] = HarborClient(url, token)


# ── register ──────────────────────────────────────────────


@cli.command()
@click.argument("agent_id")
@click.argument("name")
@click.option("--desc", default="", help="Description")
@click.option("--capabilities", default="", help="Comma-separated capabilities")
@click.option("--phases", default="", help="Comma-separated phase affinities")
@click.option("--tenant", envvar="HARBOR_TENANT", required=True, help="Tenant ID")
@click.option("--owner", envvar="HARBOR_OWNER", required=True, help="Owner ID")
@click.pass_context
def register(
    ctx: click.Context,
    agent_id: str,
    name: str,
    desc: str,
    capabilities: str,
    phases: str,
    tenant: str,
    owner: str,
) -> None:
    """Register a new agent (starts as draft)."""
    client: HarborClient = ctx.obj["client"]
    body = {
        "agent_id": agent_id,
        "name": name,
        "description": desc,
        "tenant_id": tenant,
        "owner": {"owner_id": owner, "team": "", "org_id": ""},
        "capabilities": [c.strip() for c in capabilities.split(",") if c.strip()],
        "phase_affinity": [p.strip() for p in phases.split(",") if p.strip()],
    }
    result = client.post("/agents", body)
    click.secho(
        f"✓ Registered {result['agent_id']} (lifecycle: {result['lifecycle_status']})", fg="green"
    )


# ── list ──────────────────────────────────────────────────


@cli.command("list")
@click.option(
    "--lifecycle",
    type=click.Choice(
        [
            "draft",
            "submitted",
            "in_review",
            "approved",
            "published",
            "suspended",
            "deprecated",
            "retired",
        ]
    ),
    default=None,
)
@click.option("--limit", default=20, help="Max results")
@click.pass_context
def list_agents(ctx: click.Context, lifecycle: str | None, limit: int) -> None:
    """List agents."""
    client: HarborClient = ctx.obj["client"]
    params = f"?limit={limit}"
    if lifecycle:
        params += f"&lifecycle={lifecycle}"
    data = client.get(f"/agents{params}")
    agents = data.get("items", [])
    if not agents:
        click.echo("No agents found.")
        return
    for a in agents:
        status_color = {"published": "green", "draft": "white", "suspended": "red"}.get(
            a["lifecycle_status"], "yellow"
        )
        click.echo(f"  {a['agent_id']:<30} ", nl=False)
        click.secho(f"{a['lifecycle_status']:<12}", fg=status_color, nl=False)
        click.echo(f" {a['name']}")


# ── status ────────────────────────────────────────────────


@cli.command()
@click.argument("agent_id")
@click.pass_context
def status(ctx: click.Context, agent_id: str) -> None:
    """Show agent detail and health."""
    client: HarborClient = ctx.obj["client"]
    agent = client.get(f"/agents/{agent_id}")
    click.echo(f"Agent:      {agent['name']} ({agent['agent_id']})")
    click.echo(f"Lifecycle:  {agent['lifecycle_status']}")
    click.echo(f"Visibility: {agent['visibility']}")
    click.echo(f"Version:    {agent['version']}")
    if agent.get("capabilities"):
        click.echo(f"Caps:       {', '.join(agent['capabilities'])}")
    if agent.get("phase_affinity"):
        click.echo(f"Phases:     {', '.join(agent['phase_affinity'])}")
    click.echo(f"Updated:    {agent['updated_at']}")


# ── lifecycle ─────────────────────────────────────────────


@cli.command()
@click.argument("agent_id")
@click.argument(
    "target",
    type=click.Choice(
        [
            "submitted",
            "in_review",
            "approved",
            "published",
            "suspended",
            "deprecated",
            "retired",
            "draft",
        ]
    ),
)
@click.option("--reason", default="", help="Reason for transition")
@click.pass_context
def lifecycle(ctx: click.Context, agent_id: str, target: str, reason: str) -> None:
    """Transition agent lifecycle state."""
    client: HarborClient = ctx.obj["client"]
    result = client.put(f"/agents/{agent_id}/lifecycle?target={target}&reason={reason}")
    click.secho(f"✓ {agent_id} → {result['lifecycle_status']}", fg="green")


# ── discover ──────────────────────────────────────────────


@cli.command()
@click.option("--capability", "-c", default=None, help="Search by capability")
@click.option("--phase", "-p", default=None, help="Search by phase")
@click.option("--resolve", is_flag=True, help="Resolve best agent")
@click.pass_context
def discover(ctx: click.Context, capability: str | None, phase: str | None, resolve: bool) -> None:
    """Discover agents by capability or phase."""
    client: HarborClient = ctx.obj["client"]
    if resolve:
        params = []
        if capability:
            params.append(f"capability={capability}")
        if phase:
            params.append(f"phase={phase}")
        result = client.get(f"/discover/resolve?{'&'.join(params)}")
        if result:
            click.secho(f"✓ Best: {result['agent_id']} — {result['name']}", fg="green")
        else:
            click.echo("No matching agent found.")
    elif capability:
        agents = client.get(f"/discover/capability/{capability}")
        for a in agents:
            click.echo(f"  {a['agent_id']:<30} {a['name']}")
    elif phase:
        agents = client.get(f"/discover/phase/{phase}")
        for a in agents:
            click.echo(f"  {a['agent_id']:<30} {a['name']}")
    else:
        click.echo("Specify --capability or --phase")


# ── health ────────────────────────────────────────────────


@cli.command()
@click.argument("agent_id", required=False)
@click.pass_context
def health(ctx: click.Context, agent_id: str | None) -> None:
    """Show health summary or send heartbeat for an agent."""
    client: HarborClient = ctx.obj["client"]
    if agent_id:
        result = client.put(f"/agents/{agent_id}/health")
        click.secho(f"✓ Heartbeat sent — {result['state']}", fg="green")
    else:
        summary = client.get("/health/summary")
        for k, v in summary.items():
            color = {"healthy": "green", "unhealthy": "red"}.get(k, "white")
            click.echo(f"  {k:<12} ", nl=False)
            click.secho(str(v), fg=color)


def main() -> None:
    """Entry point."""
    cli()
