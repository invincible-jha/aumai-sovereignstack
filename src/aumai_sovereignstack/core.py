"""Core logic for aumai-sovereignstack."""

from __future__ import annotations

from aumai_sovereignstack.models import (
    ComplianceCheck,
    DeploymentConfig,
    DeploymentReport,
    SovereignRegion,
)

# ---------------------------------------------------------------------------
# Pre-built region definitions
# ---------------------------------------------------------------------------

_INDIA = SovereignRegion(
    region_id="in",
    name="India",
    country_code="IN",
    data_residency_required=True,
    compliance_frameworks=["DPDP Act 2023", "IT Act 2000", "RBI Data Localisation"],
)

_EU = SovereignRegion(
    region_id="eu",
    name="European Union",
    country_code="EU",
    data_residency_required=True,
    compliance_frameworks=["GDPR", "EU AI Act", "NIS2 Directive"],
)

_US = SovereignRegion(
    region_id="us",
    name="United States",
    country_code="US",
    data_residency_required=False,
    compliance_frameworks=["CCPA", "HIPAA", "FedRAMP", "SOC 2"],
)

_SINGAPORE = SovereignRegion(
    region_id="sg",
    name="Singapore",
    country_code="SG",
    data_residency_required=False,
    compliance_frameworks=["PDPA", "MAS TRM", "CSA Cybersecurity Act"],
)

_UAE = SovereignRegion(
    region_id="ae",
    name="United Arab Emirates",
    country_code="AE",
    data_residency_required=True,
    compliance_frameworks=["UAE PDPL", "TDRA Cloud Regulations", "DIFC PDPL"],
)


class RegionNotFoundError(KeyError):
    """Raised when a country code does not map to a known region."""


class RegionRegistry:
    """Registry of sovereign regions with pre-built entries for major jurisdictions.

    Pre-built regions: India (DPDP Act), EU (GDPR), US, Singapore, UAE.
    """

    def __init__(self) -> None:
        self._regions: dict[str, SovereignRegion] = {}
        for region in [_INDIA, _EU, _US, _SINGAPORE, _UAE]:
            self._regions[region.country_code.upper()] = region

    def register_region(self, region: SovereignRegion) -> None:
        """Add or overwrite a region entry.

        Args:
            region: The region to register.
        """
        self._regions[region.country_code.upper()] = region

    def get_region(self, country_code: str) -> SovereignRegion:
        """Look up a region by its ISO country code.

        Args:
            country_code: ISO 3166-1 alpha-2 code (e.g. ``"IN"``, ``"DE"``).

        Returns:
            The matching ``SovereignRegion``.

        Raises:
            RegionNotFoundError: If the code is not registered.
        """
        try:
            return self._regions[country_code.upper()]
        except KeyError:
            raise RegionNotFoundError(
                f"No region registered for country code '{country_code}'."
            ) from None

    def list_regions(self) -> list[SovereignRegion]:
        """Return all registered regions sorted by region_id.

        Returns:
            List of all ``SovereignRegion`` objects.
        """
        return sorted(self._regions.values(), key=lambda r: r.region_id)


class SovereignDeployer:
    """Orchestrates sovereign AI deployments with compliance validation."""

    def create_config(
        self,
        name: str,
        region: SovereignRegion,
        infrastructure: dict[str, object] | None = None,
        model_configs: list[dict[str, object]] | None = None,
        data_policies: dict[str, object] | None = None,
    ) -> DeploymentConfig:
        """Build a new deployment configuration for the specified region.

        Args:
            name: Deployment name.
            region: Target sovereign region.
            infrastructure: Optional infrastructure descriptor.
            model_configs: Optional per-model configurations.
            data_policies: Optional data handling policies.

        Returns:
            A populated ``DeploymentConfig``.
        """
        return DeploymentConfig(
            name=name,
            region=region,
            infrastructure=infrastructure or {},
            model_configs=model_configs or [],
            data_policies=data_policies or {},
        )

    def validate_compliance(self, config: DeploymentConfig) -> list[ComplianceCheck]:
        """Run all applicable compliance checks for a deployment config.

        Args:
            config: The deployment configuration to evaluate.

        Returns:
            List of ``ComplianceCheck`` results.
        """
        checks: list[ComplianceCheck] = []
        checks.append(self.check_data_residency(config))
        for framework in config.region.compliance_frameworks:
            checks.extend(self._checks_for_framework(config, framework))
        return checks

    def check_data_residency(self, config: DeploymentConfig) -> ComplianceCheck:
        """Verify that the deployment satisfies data residency requirements.

        If the region requires data residency, ``data_policies`` must contain
        ``"data_residency": true``.

        Args:
            config: The deployment config to inspect.

        Returns:
            A ``ComplianceCheck`` indicating pass or fail.
        """
        framework = "Data Residency"
        if not config.region.data_residency_required:
            return ComplianceCheck(
                check_name="data_residency_not_required",
                passed=True,
                details=f"Region '{config.region.name}' does not mandate data residency.",
                framework=framework,
            )

        policy_value = config.data_policies.get("data_residency")
        passed = policy_value is True
        return ComplianceCheck(
            check_name="data_residency_enforced",
            passed=passed,
            details=(
                "data_policies['data_residency'] is set to True — compliant."
                if passed
                else (
                    f"Region '{config.region.name}' requires data residency but"
                    " data_policies['data_residency'] is not set to True."
                )
            ),
            framework=framework,
        )

    def generate_report(self, config: DeploymentConfig) -> DeploymentReport:
        """Generate a full compliance report for the given deployment config.

        Args:
            config: The deployment configuration to evaluate.

        Returns:
            A ``DeploymentReport`` summarising all checks.
        """
        compliance_results = self.validate_compliance(config)
        all_compliant = all(check.passed for check in compliance_results)
        return DeploymentReport(
            config=config,
            compliance_results=compliance_results,
            all_compliant=all_compliant,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _checks_for_framework(
        self, config: DeploymentConfig, framework: str
    ) -> list[ComplianceCheck]:
        upper_framework = framework.upper()

        if "GDPR" in upper_framework:
            return self._gdpr_checks(config, framework)
        if "DPDP" in upper_framework:
            return self._dpdp_checks(config, framework)
        if "HIPAA" in upper_framework:
            return self._hipaa_checks(config, framework)
        if "PDPA" in upper_framework:
            return self._pdpa_checks(config, framework)
        if "UAE PDPL" in upper_framework or "TDRA" in upper_framework:
            return self._uae_checks(config, framework)

        return [
            ComplianceCheck(
                check_name=f"{framework.lower().replace(' ', '_')}_acknowledged",
                passed=True,
                details=f"Framework '{framework}' noted; no automated checks configured.",
                framework=framework,
            )
        ]

    def _gdpr_checks(
        self, config: DeploymentConfig, framework: str
    ) -> list[ComplianceCheck]:
        has_dpa = bool(config.data_policies.get("data_protection_officer"))
        has_lawful_basis = bool(config.data_policies.get("lawful_basis"))
        return [
            ComplianceCheck(
                check_name="gdpr_dpo_designated",
                passed=has_dpa,
                details=(
                    "Data Protection Officer is designated."
                    if has_dpa
                    else "data_policies['data_protection_officer'] must be set for GDPR."
                ),
                framework=framework,
            ),
            ComplianceCheck(
                check_name="gdpr_lawful_basis_defined",
                passed=has_lawful_basis,
                details=(
                    "Lawful basis for processing is defined."
                    if has_lawful_basis
                    else "data_policies['lawful_basis'] must be set for GDPR."
                ),
                framework=framework,
            ),
        ]

    def _dpdp_checks(
        self, config: DeploymentConfig, framework: str
    ) -> list[ComplianceCheck]:
        has_consent = bool(config.data_policies.get("consent_mechanism"))
        is_india_region = config.region.country_code.upper() == "IN"
        return [
            ComplianceCheck(
                check_name="dpdp_consent_mechanism",
                passed=has_consent,
                details=(
                    "Consent mechanism is configured."
                    if has_consent
                    else "data_policies['consent_mechanism'] required by DPDP Act."
                ),
                framework=framework,
            ),
            ComplianceCheck(
                check_name="dpdp_data_fiduciary_in_india",
                passed=is_india_region,
                details=(
                    "Deployment is in India — data fiduciary obligations apply."
                    if is_india_region
                    else "DPDP Act applies only to India-region deployments."
                ),
                framework=framework,
            ),
        ]

    def _hipaa_checks(
        self, config: DeploymentConfig, framework: str
    ) -> list[ComplianceCheck]:
        has_phi_controls = bool(config.data_policies.get("phi_access_controls"))
        return [
            ComplianceCheck(
                check_name="hipaa_phi_access_controls",
                passed=has_phi_controls,
                details=(
                    "PHI access controls are configured."
                    if has_phi_controls
                    else "data_policies['phi_access_controls'] required for HIPAA."
                ),
                framework=framework,
            )
        ]

    def _pdpa_checks(
        self, config: DeploymentConfig, framework: str
    ) -> list[ComplianceCheck]:
        has_purpose_limitation = bool(config.data_policies.get("purpose_limitation"))
        return [
            ComplianceCheck(
                check_name="pdpa_purpose_limitation",
                passed=has_purpose_limitation,
                details=(
                    "Purpose limitation policy is defined."
                    if has_purpose_limitation
                    else "data_policies['purpose_limitation'] required for PDPA."
                ),
                framework=framework,
            )
        ]

    def _uae_checks(
        self, config: DeploymentConfig, framework: str
    ) -> list[ComplianceCheck]:
        has_cross_border = bool(
            config.data_policies.get("cross_border_transfer_controls")
        )
        return [
            ComplianceCheck(
                check_name="uae_cross_border_transfer_controls",
                passed=has_cross_border,
                details=(
                    "Cross-border transfer controls are in place."
                    if has_cross_border
                    else (
                        "data_policies['cross_border_transfer_controls'] required"
                        " for UAE PDPL / TDRA."
                    )
                ),
                framework=framework,
            )
        ]


__all__ = [
    "RegionNotFoundError",
    "RegionRegistry",
    "SovereignDeployer",
]
