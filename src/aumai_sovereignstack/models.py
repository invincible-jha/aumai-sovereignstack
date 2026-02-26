"""Pydantic models for aumai-sovereignstack."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SovereignRegion(BaseModel):
    """Represents a national or organisational sovereign region."""

    region_id: str = Field(..., description="Unique identifier for the region.")
    name: str = Field(..., description="Human-readable region name.")
    country_code: str = Field(
        ..., min_length=2, max_length=3, description="ISO 3166-1 alpha-2 or alpha-3 code."
    )
    data_residency_required: bool = Field(
        default=False,
        description="Whether data must physically remain inside this region.",
    )
    compliance_frameworks: list[str] = Field(
        default_factory=list,
        description="List of applicable compliance framework names.",
    )


class DeploymentConfig(BaseModel):
    """Configuration for a sovereign AI deployment."""

    name: str = Field(..., description="Deployment name.")
    region: SovereignRegion = Field(..., description="Target sovereign region.")
    infrastructure: dict[str, object] = Field(
        default_factory=dict,
        description="Key/value map describing infrastructure properties.",
    )
    model_configs: list[dict[str, object]] = Field(
        default_factory=list,
        description="Per-model configuration entries.",
    )
    data_policies: dict[str, object] = Field(
        default_factory=dict,
        description="Data handling policy rules.",
    )


class ComplianceCheck(BaseModel):
    """Result of a single compliance rule evaluation."""

    check_name: str = Field(..., description="Name of the compliance check.")
    passed: bool = Field(..., description="Whether the check passed.")
    details: str = Field(..., description="Human-readable explanation.")
    framework: str = Field(..., description="Compliance framework this check belongs to.")


class DeploymentReport(BaseModel):
    """Full compliance report for a deployment configuration."""

    config: DeploymentConfig = Field(..., description="The evaluated deployment config.")
    compliance_results: list[ComplianceCheck] = Field(
        default_factory=list,
        description="All individual compliance check results.",
    )
    all_compliant: bool = Field(
        ..., description="True only if every compliance check passed."
    )


__all__ = [
    "ComplianceCheck",
    "DeploymentConfig",
    "DeploymentReport",
    "SovereignRegion",
]
