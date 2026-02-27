"""Tests for aumai-sovereignstack CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from aumai_sovereignstack.cli import main
from aumai_sovereignstack.models import DeploymentConfig, SovereignRegion


def _extract_json_list(text: str) -> list:  # type: ignore[type-arg]
    """Extract first JSON array from text."""
    start = text.index("[")
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("No JSON array found")


def _extract_json(text: str) -> dict:  # type: ignore[type-arg]
    start = text.index("{")
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("No JSON object found")


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _make_deploy_json(
    tmp_path: Path,
    region_dict: dict,  # type: ignore[type-arg]
    data_policies: dict,  # type: ignore[type-arg]
    filename: str = "deploy.json",
) -> Path:
    config = {
        "name": "Test Deployment",
        "region": region_dict,
        "data_policies": data_policies,
    }
    path = tmp_path / filename
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# --version
# ---------------------------------------------------------------------------


def test_cli_version(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


# ---------------------------------------------------------------------------
# regions command
# ---------------------------------------------------------------------------


def test_regions_no_flags(runner: CliRunner) -> None:
    result = runner.invoke(main, ["regions"])
    assert result.exit_code == 0
    assert "Specify --list" in result.output


def test_regions_list(runner: CliRunner) -> None:
    result = runner.invoke(main, ["regions", "--list"])
    assert result.exit_code == 0
    assert "IN" in result.output or "India" in result.output
    assert "EU" in result.output or "European Union" in result.output


def test_regions_country_lookup_india(runner: CliRunner) -> None:
    result = runner.invoke(main, ["regions", "--country", "IN"])
    assert result.exit_code == 0
    data = _extract_json(result.output)
    assert data["country_code"] == "IN"


def test_regions_country_lookup_eu(runner: CliRunner) -> None:
    result = runner.invoke(main, ["regions", "--country", "EU"])
    assert result.exit_code == 0
    data = _extract_json(result.output)
    assert "GDPR" in data["compliance_frameworks"]


def test_regions_country_lookup_case_insensitive(runner: CliRunner) -> None:
    result = runner.invoke(main, ["regions", "--country", "in"])
    assert result.exit_code == 0


def test_regions_unknown_country(runner: CliRunner) -> None:
    result = runner.invoke(main, ["regions", "--country", "ZZ"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# deploy command
# ---------------------------------------------------------------------------


def test_deploy_compliant(runner: CliRunner, tmp_path: Path) -> None:
    config_path = _make_deploy_json(
        tmp_path,
        region_dict={
            "region_id": "us",
            "name": "United States",
            "country_code": "US",
            "data_residency_required": False,
            "compliance_frameworks": ["CCPA"],
        },
        data_policies={},
    )
    result = runner.invoke(main, ["deploy", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "PASS" in result.output


def test_deploy_noncompliant_exits_nonzero(runner: CliRunner, tmp_path: Path) -> None:
    config_path = _make_deploy_json(
        tmp_path,
        region_dict={
            "region_id": "in",
            "name": "India",
            "country_code": "IN",
            "data_residency_required": True,
            "compliance_frameworks": ["DPDP Act 2023"],
        },
        data_policies={},  # no data_residency
    )
    result = runner.invoke(main, ["deploy", "--config", str(config_path)])
    assert result.exit_code != 0


def test_deploy_invalid_json(runner: CliRunner, tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{bad json}", encoding="utf-8")
    result = runner.invoke(main, ["deploy", "--config", str(bad_file)])
    assert result.exit_code != 0


def test_deploy_non_object_json(runner: CliRunner, tmp_path: Path) -> None:
    arr_file = tmp_path / "arr.json"
    arr_file.write_text("[1, 2, 3]", encoding="utf-8")
    result = runner.invoke(main, ["deploy", "--config", str(arr_file)])
    assert result.exit_code != 0


def test_deploy_missing_required_field(runner: CliRunner, tmp_path: Path) -> None:
    config = {"name": "Bad"}  # missing region
    bad_file = tmp_path / "incomplete.json"
    bad_file.write_text(json.dumps(config), encoding="utf-8")
    result = runner.invoke(main, ["deploy", "--config", str(bad_file)])
    assert result.exit_code != 0


def test_deploy_shows_check_results(runner: CliRunner, tmp_path: Path) -> None:
    config_path = _make_deploy_json(
        tmp_path,
        region_dict={
            "region_id": "us",
            "name": "United States",
            "country_code": "US",
            "data_residency_required": False,
            "compliance_frameworks": [],
        },
        data_policies={},
    )
    result = runner.invoke(main, ["deploy", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "Test Deployment" in result.output
    assert "United States" in result.output


# ---------------------------------------------------------------------------
# compliance command
# ---------------------------------------------------------------------------


def test_compliance_outputs_json(runner: CliRunner, tmp_path: Path) -> None:
    config_path = _make_deploy_json(
        tmp_path,
        region_dict={
            "region_id": "us",
            "name": "United States",
            "country_code": "US",
            "data_residency_required": False,
            "compliance_frameworks": [],
        },
        data_policies={},
    )
    result = runner.invoke(main, ["compliance", "--config", str(config_path)])
    assert result.exit_code == 0
    checks = _extract_json_list(result.output)
    assert isinstance(checks, list)
    assert all("check_name" in c for c in checks)


def test_compliance_noncompliant_exits_nonzero(
    runner: CliRunner, tmp_path: Path
) -> None:
    config_path = _make_deploy_json(
        tmp_path,
        region_dict={
            "region_id": "in",
            "name": "India",
            "country_code": "IN",
            "data_residency_required": True,
            "compliance_frameworks": ["DPDP Act 2023"],
        },
        data_policies={},
    )
    result = runner.invoke(main, ["compliance", "--config", str(config_path)])
    assert result.exit_code != 0


def test_compliance_invalid_json(runner: CliRunner, tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not json", encoding="utf-8")
    result = runner.invoke(main, ["compliance", "--config", str(bad_file)])
    assert result.exit_code != 0


def test_compliance_non_object_json(runner: CliRunner, tmp_path: Path) -> None:
    arr_file = tmp_path / "arr.json"
    arr_file.write_text("[1, 2]", encoding="utf-8")
    result = runner.invoke(main, ["compliance", "--config", str(arr_file)])
    assert result.exit_code != 0
