"""Tests for aumai-sovereignstack core module."""

from __future__ import annotations

import pytest

from aumai_sovereignstack.core import (
    RegionNotFoundError,
    RegionRegistry,
    SovereignDeployer,
)
from aumai_sovereignstack.models import (
    ComplianceCheck,
    DeploymentConfig,
    DeploymentReport,
    SovereignRegion,
)


# ---------------------------------------------------------------------------
# SovereignRegion model tests
# ---------------------------------------------------------------------------


class TestSovereignRegionModel:
    def test_valid_creation(self, india_region: SovereignRegion) -> None:
        assert india_region.region_id == "in"
        assert india_region.country_code == "IN"
        assert india_region.data_residency_required is True

    def test_default_no_residency(self) -> None:
        region = SovereignRegion(
            region_id="xx",
            name="Test Country",
            country_code="XX",
        )
        assert region.data_residency_required is False

    def test_country_code_too_long_raises(self) -> None:
        with pytest.raises(Exception):
            SovereignRegion(
                region_id="x",
                name="X",
                country_code="XXXX",  # max is 3
            )

    def test_compliance_frameworks_default_empty(self) -> None:
        region = SovereignRegion(
            region_id="xx",
            name="Test",
            country_code="XX",
        )
        assert region.compliance_frameworks == []


# ---------------------------------------------------------------------------
# RegionRegistry tests
# ---------------------------------------------------------------------------


class TestRegionRegistry:
    def test_pre_built_india(self) -> None:
        registry = RegionRegistry()
        region = registry.get_region("IN")
        assert region.country_code == "IN"
        assert region.data_residency_required is True

    def test_pre_built_eu(self) -> None:
        registry = RegionRegistry()
        region = registry.get_region("EU")
        assert region.country_code == "EU"
        assert "GDPR" in region.compliance_frameworks

    def test_pre_built_us(self) -> None:
        registry = RegionRegistry()
        region = registry.get_region("US")
        assert region.data_residency_required is False

    def test_pre_built_singapore(self) -> None:
        registry = RegionRegistry()
        region = registry.get_region("SG")
        assert "PDPA" in region.compliance_frameworks

    def test_pre_built_uae(self) -> None:
        registry = RegionRegistry()
        region = registry.get_region("AE")
        assert region.data_residency_required is True

    def test_get_region_case_insensitive(self) -> None:
        registry = RegionRegistry()
        region = registry.get_region("in")
        assert region.country_code == "IN"

    def test_get_region_missing_raises(self) -> None:
        registry = RegionRegistry()
        with pytest.raises(RegionNotFoundError):
            registry.get_region("ZZ")

    def test_get_region_error_message(self) -> None:
        registry = RegionRegistry()
        with pytest.raises(RegionNotFoundError, match="ZZ"):
            registry.get_region("ZZ")

    def test_register_custom_region(self) -> None:
        registry = RegionRegistry()
        custom = SovereignRegion(
            region_id="br",
            name="Brazil",
            country_code="BR",
            data_residency_required=False,
            compliance_frameworks=["LGPD"],
        )
        registry.register_region(custom)
        retrieved = registry.get_region("BR")
        assert retrieved.name == "Brazil"

    def test_register_overwrites_existing(self) -> None:
        registry = RegionRegistry()
        updated_india = SovereignRegion(
            region_id="in-v2",
            name="India Updated",
            country_code="IN",
            data_residency_required=True,
            compliance_frameworks=["DPDP Act 2023", "Updated Law"],
        )
        registry.register_region(updated_india)
        region = registry.get_region("IN")
        assert region.name == "India Updated"

    def test_list_regions_returns_all_prebuilt(self) -> None:
        registry = RegionRegistry()
        regions = registry.list_regions()
        country_codes = {r.country_code for r in regions}
        assert "IN" in country_codes
        assert "EU" in country_codes
        assert "US" in country_codes
        assert "SG" in country_codes
        assert "AE" in country_codes

    def test_list_regions_sorted_by_region_id(self) -> None:
        registry = RegionRegistry()
        regions = registry.list_regions()
        ids = [r.region_id for r in regions]
        assert ids == sorted(ids)


# ---------------------------------------------------------------------------
# SovereignDeployer tests
# ---------------------------------------------------------------------------


class TestSovereignDeployer:
    def test_create_config(self, india_region: SovereignRegion) -> None:
        deployer = SovereignDeployer()
        config = deployer.create_config("Test Deploy", india_region)
        assert config.name == "Test Deploy"
        assert config.region.country_code == "IN"
        assert config.infrastructure == {}
        assert config.model_configs == []
        assert config.data_policies == {}

    def test_create_config_with_options(self, india_region: SovereignRegion) -> None:
        deployer = SovereignDeployer()
        config = deployer.create_config(
            "Full Deploy",
            india_region,
            infrastructure={"provider": "aws"},
            model_configs=[{"model": "llm-v1"}],
            data_policies={"data_residency": True},
        )
        assert config.infrastructure == {"provider": "aws"}
        assert config.model_configs == [{"model": "llm-v1"}]
        assert config.data_policies["data_residency"] is True

    # -- check_data_residency tests --

    def test_data_residency_not_required(self, us_region: SovereignRegion) -> None:
        deployer = SovereignDeployer()
        config = DeploymentConfig(name="US Deploy", region=us_region)
        check = deployer.check_data_residency(config)
        assert check.passed is True
        assert check.check_name == "data_residency_not_required"

    def test_data_residency_required_and_set(
        self, india_region: SovereignRegion
    ) -> None:
        deployer = SovereignDeployer()
        config = DeploymentConfig(
            name="India Deploy",
            region=india_region,
            data_policies={"data_residency": True},
        )
        check = deployer.check_data_residency(config)
        assert check.passed is True
        assert check.check_name == "data_residency_enforced"

    def test_data_residency_required_but_missing(
        self, india_region: SovereignRegion
    ) -> None:
        deployer = SovereignDeployer()
        config = DeploymentConfig(name="India Bad", region=india_region)
        check = deployer.check_data_residency(config)
        assert check.passed is False

    def test_data_residency_required_but_false(
        self, india_region: SovereignRegion
    ) -> None:
        deployer = SovereignDeployer()
        config = DeploymentConfig(
            name="India Bad",
            region=india_region,
            data_policies={"data_residency": False},
        )
        check = deployer.check_data_residency(config)
        assert check.passed is False

    # -- validate_compliance tests (full suite per region) --

    def test_validate_compliance_india_compliant(
        self, compliant_india_config: DeploymentConfig
    ) -> None:
        deployer = SovereignDeployer()
        checks = deployer.validate_compliance(compliant_india_config)
        assert isinstance(checks, list)
        assert all(isinstance(c, ComplianceCheck) for c in checks)
        # data_residency + DPDP Act 2023 + IT Act 2000 checks
        check_names = {c.check_name for c in checks}
        assert "data_residency_enforced" in check_names
        assert "dpdp_consent_mechanism" in check_names
        assert "dpdp_data_fiduciary_in_india" in check_names

    def test_validate_compliance_india_noncompliant(
        self, noncompliant_india_config: DeploymentConfig
    ) -> None:
        deployer = SovereignDeployer()
        checks = deployer.validate_compliance(noncompliant_india_config)
        failed = [c for c in checks if not c.passed]
        assert len(failed) > 0

    def test_validate_compliance_eu_gdpr(self, eu_region: SovereignRegion) -> None:
        deployer = SovereignDeployer()
        config = DeploymentConfig(
            name="EU Deploy",
            region=eu_region,
            data_policies={
                "data_residency": True,
                "data_protection_officer": "dpo@company.eu",
                "lawful_basis": "legitimate_interest",
            },
        )
        checks = deployer.validate_compliance(config)
        check_names = {c.check_name for c in checks}
        assert "gdpr_dpo_designated" in check_names
        assert "gdpr_lawful_basis_defined" in check_names
        # All should pass
        failed = [c for c in checks if not c.passed]
        assert failed == []

    def test_validate_compliance_eu_gdpr_missing_dpo(
        self, eu_region: SovereignRegion
    ) -> None:
        deployer = SovereignDeployer()
        config = DeploymentConfig(
            name="EU Bad",
            region=eu_region,
            data_policies={"data_residency": True, "lawful_basis": "consent"},
        )
        checks = deployer.validate_compliance(config)
        dpo_check = next(c for c in checks if c.check_name == "gdpr_dpo_designated")
        assert dpo_check.passed is False

    def test_validate_compliance_us_hipaa(self, us_region: SovereignRegion) -> None:
        deployer = SovereignDeployer()
        config = DeploymentConfig(
            name="US Deploy",
            region=us_region,
            data_policies={"phi_access_controls": "strict"},
        )
        checks = deployer.validate_compliance(config)
        hipaa_check = next(
            (c for c in checks if c.check_name == "hipaa_phi_access_controls"), None
        )
        assert hipaa_check is not None
        assert hipaa_check.passed is True

    def test_validate_compliance_singapore_pdpa(
        self, singapore_region: SovereignRegion
    ) -> None:
        deployer = SovereignDeployer()
        config = DeploymentConfig(
            name="SG Deploy",
            region=singapore_region,
            data_policies={"purpose_limitation": "data_science_only"},
        )
        checks = deployer.validate_compliance(config)
        pdpa_check = next(
            (c for c in checks if c.check_name == "pdpa_purpose_limitation"), None
        )
        assert pdpa_check is not None
        assert pdpa_check.passed is True

    def test_validate_compliance_uae(self, uae_region: SovereignRegion) -> None:
        deployer = SovereignDeployer()
        config = DeploymentConfig(
            name="UAE Deploy",
            region=uae_region,
            data_policies={
                "data_residency": True,
                "cross_border_transfer_controls": True,
            },
        )
        checks = deployer.validate_compliance(config)
        uae_check = next(
            (
                c
                for c in checks
                if c.check_name == "uae_cross_border_transfer_controls"
            ),
            None,
        )
        assert uae_check is not None
        assert uae_check.passed is True

    def test_validate_compliance_unknown_framework(self) -> None:
        """Unknown frameworks produce an acknowledged (passing) check."""
        deployer = SovereignDeployer()
        custom_region = SovereignRegion(
            region_id="xx",
            name="Test Country",
            country_code="XX",
            data_residency_required=False,
            compliance_frameworks=["Some Unknown Framework 2025"],
        )
        config = DeploymentConfig(name="Test", region=custom_region)
        checks = deployer.validate_compliance(config)
        unknown_check = next(
            (c for c in checks if "acknowledged" in c.check_name), None
        )
        assert unknown_check is not None
        assert unknown_check.passed is True

    # -- generate_report tests --

    def test_generate_report_all_compliant(
        self, compliant_india_config: DeploymentConfig
    ) -> None:
        deployer = SovereignDeployer()
        report = deployer.generate_report(compliant_india_config)
        assert isinstance(report, DeploymentReport)
        assert report.all_compliant is True

    def test_generate_report_not_compliant(
        self, noncompliant_india_config: DeploymentConfig
    ) -> None:
        deployer = SovereignDeployer()
        report = deployer.generate_report(noncompliant_india_config)
        assert report.all_compliant is False
        assert len(report.compliance_results) > 0

    def test_generate_report_contains_config(
        self, compliant_india_config: DeploymentConfig
    ) -> None:
        deployer = SovereignDeployer()
        report = deployer.generate_report(compliant_india_config)
        assert report.config.name == compliant_india_config.name
