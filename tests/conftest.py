"""Shared test fixtures for aumai-sovereignstack."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aumai_sovereignstack.models import (
    ComplianceCheck,
    DeploymentConfig,
    SovereignRegion,
)


@pytest.fixture()
def india_region() -> SovereignRegion:
    return SovereignRegion(
        region_id="in",
        name="India",
        country_code="IN",
        data_residency_required=True,
        compliance_frameworks=["DPDP Act 2023", "IT Act 2000"],
    )


@pytest.fixture()
def eu_region() -> SovereignRegion:
    return SovereignRegion(
        region_id="eu",
        name="European Union",
        country_code="EU",
        data_residency_required=True,
        compliance_frameworks=["GDPR", "EU AI Act"],
    )


@pytest.fixture()
def us_region() -> SovereignRegion:
    return SovereignRegion(
        region_id="us",
        name="United States",
        country_code="US",
        data_residency_required=False,
        compliance_frameworks=["HIPAA", "CCPA"],
    )


@pytest.fixture()
def singapore_region() -> SovereignRegion:
    return SovereignRegion(
        region_id="sg",
        name="Singapore",
        country_code="SG",
        data_residency_required=False,
        compliance_frameworks=["PDPA"],
    )


@pytest.fixture()
def uae_region() -> SovereignRegion:
    return SovereignRegion(
        region_id="ae",
        name="United Arab Emirates",
        country_code="AE",
        data_residency_required=True,
        compliance_frameworks=["UAE PDPL", "TDRA Cloud Regulations"],
    )


@pytest.fixture()
def compliant_india_config(india_region: SovereignRegion) -> DeploymentConfig:
    return DeploymentConfig(
        name="India AI Deployment",
        region=india_region,
        data_policies={
            "data_residency": True,
            "consent_mechanism": "explicit_opt_in",
        },
    )


@pytest.fixture()
def noncompliant_india_config(india_region: SovereignRegion) -> DeploymentConfig:
    return DeploymentConfig(
        name="India AI Deployment Bad",
        region=india_region,
        data_policies={},  # missing data_residency and consent_mechanism
    )


@pytest.fixture()
def india_deploy_json(
    tmp_path: Path, compliant_india_config: DeploymentConfig
) -> Path:
    path = tmp_path / "deploy.json"
    path.write_text(compliant_india_config.model_dump_json(), encoding="utf-8")
    return path


@pytest.fixture()
def noncompliant_deploy_json(
    tmp_path: Path, noncompliant_india_config: DeploymentConfig
) -> Path:
    path = tmp_path / "deploy_bad.json"
    path.write_text(noncompliant_india_config.model_dump_json(), encoding="utf-8")
    return path
