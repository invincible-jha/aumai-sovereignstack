"""Quickstart examples for aumai-sovereignstack.

Demonstrates sovereign region lookup, custom region registration, deployment
configuration, compliance validation, and report generation across all
five pre-built jurisdictions.

Run this file directly to verify your installation:

    python examples/quickstart.py

Each demo function is self-contained and prints its own output.
"""

from __future__ import annotations

from aumai_sovereignstack import (
    ComplianceCheck,
    DeploymentConfig,
    DeploymentReport,
    RegionNotFoundError,
    RegionRegistry,
    SovereignDeployer,
    SovereignRegion,
)


# ---------------------------------------------------------------------------
# Demo 1: Explore the built-in sovereign regions
# ---------------------------------------------------------------------------


def demo_region_registry() -> None:
    """Show all pre-built regions and how to look one up by country code."""
    print("=" * 60)
    print("DEMO 1: Region Registry — Built-in Jurisdictions")
    print("=" * 60)

    registry = RegionRegistry()

    # List all built-in regions
    all_regions = registry.list_regions()
    print(f"  Pre-built regions ({len(all_regions)} total):")
    for region in all_regions:
        residency = "data-residency-required" if region.data_residency_required else "no-residency-req"
        print(f"    [{region.country_code}] {region.name}  ({residency})")
        print(f"         Frameworks: {', '.join(region.compliance_frameworks)}")

    print()

    # Look up a specific region
    eu = registry.get_region("EU")
    print(f"  get_region('EU'):")
    print(f"    name: {eu.name}")
    print(f"    data_residency_required: {eu.data_residency_required}")
    print(f"    frameworks: {eu.compliance_frameworks}")

    # Case-insensitive lookup
    india = registry.get_region("in")
    print(f"\n  get_region('in') (case-insensitive): {india.name}")

    # RegionNotFoundError for unknown code
    try:
        registry.get_region("XX")
    except RegionNotFoundError as exc:
        print(f"\n  RegionNotFoundError: {exc}")

    print()


# ---------------------------------------------------------------------------
# Demo 2: Register a custom jurisdiction
# ---------------------------------------------------------------------------


def demo_custom_region() -> None:
    """Show how to add a custom sovereign region beyond the five built-in ones."""
    print("=" * 60)
    print("DEMO 2: Custom Region Registration")
    print("=" * 60)

    registry = RegionRegistry()

    custom_regions = [
        SovereignRegion(
            region_id="br",
            name="Brazil",
            country_code="BR",
            data_residency_required=False,
            compliance_frameworks=["LGPD", "Marco Civil da Internet"],
        ),
        SovereignRegion(
            region_id="gb",
            name="United Kingdom",
            country_code="GB",
            data_residency_required=False,
            compliance_frameworks=["UK GDPR", "Data Protection Act 2018", "ICO Guidance"],
        ),
        SovereignRegion(
            region_id="ca",
            name="Canada",
            country_code="CA",
            data_residency_required=False,
            compliance_frameworks=["PIPEDA", "Quebec Law 25", "CASL"],
        ),
    ]

    for region in custom_regions:
        registry.register_region(region)
        print(f"  Registered: [{region.country_code}] {region.name}")
        print(f"    Frameworks: {', '.join(region.compliance_frameworks)}")

    # Verify lookup
    br = registry.get_region("BR")
    print(f"\n  Verified lookup: {br.name} — frameworks: {br.compliance_frameworks}")

    total = len(registry.list_regions())
    print(f"\n  Total regions in registry: {total} (5 built-in + 3 custom)")
    print()


# ---------------------------------------------------------------------------
# Demo 3: EU GDPR compliance check
# ---------------------------------------------------------------------------


def demo_eu_gdpr_compliance() -> None:
    """Show a GDPR-compliant EU deployment and what a failing check looks like."""
    print("=" * 60)
    print("DEMO 3: EU GDPR Compliance Check")
    print("=" * 60)

    registry = RegionRegistry()
    deployer = SovereignDeployer()
    eu = registry.get_region("EU")

    # --- Passing configuration ---
    passing_config = deployer.create_config(
        name="eu-document-intelligence",
        region=eu,
        infrastructure={"provider": "on-premise", "data_center": "Frankfurt"},
        model_configs=[{"model": "llama-3-70b", "serving": "vllm", "max_tokens": 2048}],
        data_policies={
            "data_residency": True,
            "data_protection_officer": "dpo@company.eu",
            "lawful_basis": "legitimate_interest",
        },
    )

    report: DeploymentReport = deployer.generate_report(passing_config)
    _print_report(report)

    # --- Failing configuration (missing DPO) ---
    failing_config = deployer.create_config(
        name="eu-document-intelligence-misconfigured",
        region=eu,
        data_policies={
            "data_residency": True,
            # data_protection_officer deliberately omitted
            "lawful_basis": "consent",
        },
    )

    failing_report = deployer.generate_report(failing_config)
    _print_report(failing_report)


# ---------------------------------------------------------------------------
# Demo 4: India DPDP Act compliance check
# ---------------------------------------------------------------------------


def demo_india_dpdp_compliance() -> None:
    """Show an India-region deployment validated against the DPDP Act."""
    print("=" * 60)
    print("DEMO 4: India DPDP Act Compliance Check")
    print("=" * 60)

    registry = RegionRegistry()
    deployer = SovereignDeployer()
    india = registry.get_region("IN")

    config = deployer.create_config(
        name="in-customer-service-ai",
        region=india,
        infrastructure={"provider": "on-premise", "data_center": "Mumbai"},
        model_configs=[{"model": "llama-3-8b-instruct", "quantization": "int8"}],
        data_policies={
            "data_residency": True,
            "consent_mechanism": "explicit_opt_in",
        },
    )

    report = deployer.generate_report(config)
    _print_report(report)

    # Individual data residency check only
    check: ComplianceCheck = deployer.check_data_residency(config)
    print(f"  Standalone data_residency check: passed={check.passed}")
    print(f"    Details: {check.details}")
    print()


# ---------------------------------------------------------------------------
# Demo 5: Multi-region sweep — same policies, all five jurisdictions
# ---------------------------------------------------------------------------


def demo_multi_region_sweep() -> None:
    """Validate the same data_policies dict against all five built-in regions."""
    print("=" * 60)
    print("DEMO 5: Multi-Region Compliance Sweep")
    print("=" * 60)

    registry = RegionRegistry()
    deployer = SovereignDeployer()

    # A policy set designed to satisfy every built-in region
    universal_policies: dict[str, object] = {
        "data_residency": True,
        "data_protection_officer": "dpo@globalcorp.com",
        "lawful_basis": "consent",
        "consent_mechanism": "explicit_opt_in",
        "phi_access_controls": "rbac_with_audit_log",
        "purpose_limitation": "stated_at_collection",
        "cross_border_transfer_controls": "contractual_safeguards_approved",
    }

    print("  Sweeping all regions with a universal policy set:\n")
    for region in registry.list_regions():
        config = deployer.create_config(
            name=f"global-ai-{region.country_code.lower()}",
            region=region,
            data_policies=universal_policies,
        )
        report = deployer.generate_report(config)
        status = "PASS" if report.all_compliant else "FAIL"
        fail_count = sum(1 for c in report.compliance_results if not c.passed)
        print(f"  [{status}] {region.name} ({region.country_code})"
              f"  — {len(report.compliance_results)} checks, {fail_count} failed")

    print()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _print_report(report: DeploymentReport) -> None:
    """Print a formatted deployment report."""
    status = "PASS" if report.all_compliant else "FAIL"
    config = report.config
    print(f"\n  Deployment: {config.name}  [{status}]")
    print(f"  Region: {config.region.name} ({config.region.country_code})")
    print(f"  Checks run: {len(report.compliance_results)}")
    for check in report.compliance_results:
        icon = "OK" if check.passed else "!!"
        print(f"    [{icon}] {check.check_name}  ({check.framework})")
        print(f"         {check.details}")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run all quickstart demos."""
    print("\naumai-sovereignstack Quickstart Examples")
    print("Version:", end=" ")
    import aumai_sovereignstack
    print(aumai_sovereignstack.__version__)
    print()

    demo_region_registry()
    demo_custom_region()
    demo_eu_gdpr_compliance()
    demo_india_dpdp_compliance()
    demo_multi_region_sweep()

    print("All demos completed successfully.")


if __name__ == "__main__":
    main()
