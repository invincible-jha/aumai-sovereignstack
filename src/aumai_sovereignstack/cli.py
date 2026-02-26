"""CLI entry point for aumai-sovereignstack."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from aumai_sovereignstack.core import (
    RegionNotFoundError,
    RegionRegistry,
    SovereignDeployer,
)
from aumai_sovereignstack.models import DeploymentConfig

_registry = RegionRegistry()
_deployer = SovereignDeployer()


@click.group()
@click.version_option()
def main() -> None:
    """AumAI Sovereign Stack — deploy AI within national data boundaries."""


@main.command("deploy")
@click.option(
    "--config",
    "config_path",
    required=True,
    type=click.Path(exists=True),
    help="Path to a JSON deployment config file.",
)
def deploy_command(config_path: str) -> None:
    """Generate a compliance report for a deployment config.

    Example: aumai-sovereignstack deploy --config deploy.json
    """
    raw_text = Path(config_path).read_text(encoding="utf-8")
    try:
        data: object = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        click.echo(f"Invalid JSON: {exc}", err=True)
        sys.exit(1)

    if not isinstance(data, dict):
        click.echo("Config must be a JSON object.", err=True)
        sys.exit(1)

    try:
        config = DeploymentConfig.model_validate(data)
    except Exception as exc:
        click.echo(f"Validation error: {exc}", err=True)
        sys.exit(1)

    report = _deployer.generate_report(config)
    status_label = "PASS" if report.all_compliant else "FAIL"
    click.echo(f"Deployment: {config.name}  [{status_label}]")
    click.echo(f"Region: {config.region.name} ({config.region.country_code})")
    click.echo(f"Total checks: {len(report.compliance_results)}")
    click.echo()
    for check in report.compliance_results:
        icon = "OK" if check.passed else "!!"
        click.echo(f"  [{icon}] {check.check_name} ({check.framework})")
        click.echo(f"       {check.details}")

    if not report.all_compliant:
        sys.exit(1)


@main.command("compliance")
@click.option(
    "--config",
    "config_path",
    required=True,
    type=click.Path(exists=True),
    help="Path to a JSON deployment config file.",
)
def compliance_command(config_path: str) -> None:
    """Run compliance checks and print results as JSON.

    Example: aumai-sovereignstack compliance --config deploy.json
    """
    raw_text = Path(config_path).read_text(encoding="utf-8")
    try:
        data: object = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        click.echo(f"Invalid JSON: {exc}", err=True)
        sys.exit(1)

    if not isinstance(data, dict):
        click.echo("Config must be a JSON object.", err=True)
        sys.exit(1)

    try:
        config = DeploymentConfig.model_validate(data)
    except Exception as exc:
        click.echo(f"Validation error: {exc}", err=True)
        sys.exit(1)

    checks = _deployer.validate_compliance(config)
    output = [check.model_dump(mode="json") for check in checks]
    click.echo(json.dumps(output, indent=2))

    if not all(check.passed for check in checks):
        sys.exit(1)


@main.command("regions")
@click.option("--list", "list_all", is_flag=True, default=False, help="List all regions.")
@click.option("--country", default=None, help="Look up a region by country code.")
def regions_command(list_all: bool, country: str | None) -> None:
    """List available sovereign regions or look up a specific one.

    Example: aumai-sovereignstack regions --list
    """
    if country:
        try:
            region = _registry.get_region(country)
        except RegionNotFoundError as exc:
            click.echo(str(exc), err=True)
            sys.exit(1)
        click.echo(json.dumps(region.model_dump(mode="json"), indent=2))
        return

    if list_all:
        for region in _registry.list_regions():
            residency_label = "data-residency-required" if region.data_residency_required else "no-residency-req"
            click.echo(
                f"[{region.country_code}] {region.name}"
                f"  ({residency_label})"
            )
            if region.compliance_frameworks:
                click.echo(f"  Frameworks: {', '.join(region.compliance_frameworks)}")
        return

    click.echo("Specify --list to list all regions or --country CODE to look up one.")


if __name__ == "__main__":
    main()
