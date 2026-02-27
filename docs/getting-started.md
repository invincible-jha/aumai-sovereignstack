# Getting Started with aumai-sovereignstack

This guide walks you from installation to your first compliance report in under 15 minutes. No cloud account, no external service, no database required.

---

## Prerequisites

- Python 3.11 or later
- pip (or your preferred package manager)
- Basic familiarity with JSON and data privacy concepts

---

## Installation

### From PyPI (recommended)

```bash
pip install aumai-sovereignstack
```

### From source

```bash
git clone https://github.com/aumai/aumai-sovereignstack.git
cd aumai-sovereignstack
pip install -e ".[dev]"
```

### Verify

```bash
aumai-sovereignstack --version
python -c "import aumai_sovereignstack; print(aumai_sovereignstack.__version__)"
```

---

## Core Concepts

**SovereignRegion** describes a national or organizational jurisdiction. It carries a `region_id`, `name`, `country_code` (ISO 3166-1), a `data_residency_required` flag, and a list of `compliance_frameworks` (the names of applicable laws and standards). Five regions are pre-built; you can add more.

**DeploymentConfig** describes your AI system. It holds the deployment `name`, the target `region`, an `infrastructure` dict for infrastructure properties, a `model_configs` list, and a `data_policies` dict. The `data_policies` dict is the primary input for automated compliance checks.

**ComplianceCheck** is the result of evaluating one compliance rule. It holds `check_name`, a `passed` boolean, a `details` string explaining the result, and the `framework` name the rule belongs to.

**DeploymentReport** is the aggregated result of running all applicable checks for a `DeploymentConfig`. It holds the `config`, a list of `compliance_results`, and an `all_compliant` boolean.

**RegionRegistry** manages the known regions. **SovereignDeployer** runs the checks.

---

## Step-by-Step Tutorial

### Step 1: Explore the built-in regions

```bash
aumai-sovereignstack regions --list
```

```
[AE] United Arab Emirates  (data-residency-required)
  Frameworks: UAE PDPL, TDRA Cloud Regulations, DIFC PDPL
[EU] European Union  (data-residency-required)
  Frameworks: GDPR, EU AI Act, NIS2 Directive
[IN] India  (data-residency-required)
  Frameworks: DPDP Act 2023, IT Act 2000, RBI Data Localisation
[SG] Singapore  (no-residency-req)
  Frameworks: PDPA, MAS TRM, CSA Cybersecurity Act
[US] United States  (no-residency-req)
  Frameworks: CCPA, HIPAA, FedRAMP, SOC 2
```

Inspect one region in detail:

```bash
aumai-sovereignstack regions --country IN
```

### Step 2: Write a deployment config

Create `deploy-india.json`:

```json
{
  "name": "in-customer-service-ai",
  "region": {
    "region_id": "in",
    "name": "India",
    "country_code": "IN",
    "data_residency_required": true,
    "compliance_frameworks": ["DPDP Act 2023", "IT Act 2000", "RBI Data Localisation"]
  },
  "infrastructure": {
    "provider": "on-premise",
    "data_center": "Mumbai"
  },
  "model_configs": [
    {
      "model": "llama-3-8b-instruct",
      "quantization": "int8",
      "max_tokens": 1024
    }
  ],
  "data_policies": {
    "data_residency": true,
    "consent_mechanism": "explicit_opt_in"
  }
}
```

### Step 3: Run the compliance check

```bash
aumai-sovereignstack deploy --config deploy-india.json
```

```
Deployment: in-customer-service-ai  [PASS]
Region: India (IN)
Total checks: 3

  [OK] data_residency_enforced (Data Residency)
       data_policies['data_residency'] is set to True — compliant.
  [OK] dpdp_consent_mechanism (DPDP Act 2023)
       Consent mechanism is configured.
  [OK] dpdp_data_fiduciary_in_india (DPDP Act 2023)
       Deployment is in India — data fiduciary obligations apply.
```

Exit code is 0 on pass, 1 on fail — suitable for CI/CD gates.

### Step 4: See what a failing check looks like

Remove `data_residency` from the config and rerun:

```bash
# Edit deploy-india.json to remove data_residency from data_policies, then:
aumai-sovereignstack deploy --config deploy-india.json
```

```
Deployment: in-customer-service-ai  [FAIL]
Region: India (IN)
Total checks: 3

  [!!] data_residency_enforced (Data Residency)
       Region 'India' requires data residency but data_policies['data_residency'] is not set to True.
  [OK] dpdp_consent_mechanism (DPDP Act 2023)
       Consent mechanism is configured.
  [OK] dpdp_data_fiduciary_in_india (DPDP Act 2023)
       Deployment is in India — data fiduciary obligations apply.
```

### Step 5: Get machine-readable output

```bash
aumai-sovereignstack compliance --config deploy-india.json
```

Returns a JSON array. Useful for programmatic processing:

```bash
# Count failing checks
aumai-sovereignstack compliance --config deploy-india.json \
  | python -c "import json,sys; data=json.load(sys.stdin); print('Failures:', sum(1 for c in data if not c['passed']))"
```

---

## Common Patterns

### Pattern 1: Run compliance checks in Python

```python
from aumai_sovereignstack import RegionRegistry, SovereignDeployer

registry = RegionRegistry()
deployer = SovereignDeployer()

eu = registry.get_region("EU")

config = deployer.create_config(
    name="eu-rag-service",
    region=eu,
    data_policies={
        "data_residency": True,
        "data_protection_officer": "dpo@mycompany.eu",
        "lawful_basis": "legitimate_interest",
    },
)

report = deployer.generate_report(config)
if not report.all_compliant:
    failures = [c for c in report.compliance_results if not c.passed]
    for failure in failures:
        print(f"FAIL: {failure.check_name} — {failure.details}")
    raise SystemExit(1)

print("Deployment is compliant. Proceeding.")
```

### Pattern 2: Multi-region deployment validation

Validate the same deployment config against multiple target regions to find the most restrictive common baseline:

```python
from aumai_sovereignstack import RegionRegistry, SovereignDeployer

registry = RegionRegistry()
deployer = SovereignDeployer()

# A data_policies dict that attempts to satisfy all regions
universal_policies: dict[str, object] = {
    "data_residency": True,
    "data_protection_officer": "dpo@company.com",
    "lawful_basis": "consent",
    "consent_mechanism": "explicit_opt_in",
    "phi_access_controls": "role_based_rbac",
    "purpose_limitation": "stated_at_collection",
    "cross_border_transfer_controls": "contractual_safeguards",
}

target_regions = ["EU", "IN", "US", "SG", "AE"]

for code in target_regions:
    region = registry.get_region(code)
    config = deployer.create_config(
        name=f"global-ai-{code.lower()}",
        region=region,
        data_policies=universal_policies,
    )
    report = deployer.generate_report(config)
    status = "PASS" if report.all_compliant else "FAIL"
    print(f"[{status}] {region.name}")
```

### Pattern 3: Register a custom jurisdiction

```python
from aumai_sovereignstack import RegionRegistry, SovereignRegion

registry = RegionRegistry()

registry.register_region(SovereignRegion(
    region_id="jp",
    name="Japan",
    country_code="JP",
    data_residency_required=False,
    compliance_frameworks=["APPI", "Cybersecurity Basic Act"],
))

jp = registry.get_region("JP")
print(jp.compliance_frameworks)  # ['APPI', 'Cybersecurity Basic Act']
```

### Pattern 4: CI/CD compliance gate

Add to your deployment pipeline (`Makefile` or CI config):

```bash
# Makefile example
.PHONY: check-compliance
check-compliance:
    aumai-sovereignstack deploy --config infra/deploy-$(REGION).json
    @echo "Compliance gate passed for region $(REGION)"
```

Or in a Python deployment script:

```python
import subprocess
import sys

result = subprocess.run(
    ["aumai-sovereignstack", "deploy", "--config", "deploy-eu.json"],
    capture_output=True,
    text=True,
)
print(result.stdout)
if result.returncode != 0:
    print("Compliance gate FAILED. Aborting deployment.")
    sys.exit(1)
```

### Pattern 5: Check data residency in isolation

For quick checks without running the full framework suite:

```python
from aumai_sovereignstack import RegionRegistry, SovereignDeployer

registry = RegionRegistry()
deployer = SovereignDeployer()

india = registry.get_region("IN")
config = deployer.create_config(
    name="test",
    region=india,
    data_policies={"data_residency": False},  # intentionally wrong
)

check = deployer.check_data_residency(config)
print(check.passed)   # False
print(check.details)  # Explains what is missing
```

---

## Troubleshooting FAQ

**Q: `RegionNotFoundError: No region registered for country code 'XX'.`**

The built-in regions use these country codes: `IN`, `EU`, `US`, `SG`, `AE`. For any other country, register a custom `SovereignRegion` with `registry.register_region(...)`. Country codes are normalized to uppercase internally, so `"eu"` and `"EU"` both work.

---

**Q: All my compliance checks are passing even though I have empty `data_policies`.**

Checks for optional frameworks (EU AI Act, NIS2, IT Act, RBI, CCPA, FedRAMP, SOC 2, MAS TRM, CSA, DIFC PDPL) are "acknowledged" checks that always pass. Only checks with an explicit policy key requirement can fail. Review the compliance framework coverage table in the README to see which keys are needed.

---

**Q: The `deploy` command exits with code 1 but I cannot see what failed.**

Use `--config` with `compliance` instead of `deploy` to get JSON output, then filter for `"passed": false`:

```bash
aumai-sovereignstack compliance --config deploy.json \
  | python -c "import json,sys; [print(c) for c in json.load(sys.stdin) if not c['passed']]"
```

---

**Q: `DeploymentConfig` Pydantic validation fails when loading from JSON.**

The `region` field expects a full nested `SovereignRegion` object. You must embed the region as a nested JSON object with `region_id`, `name`, `country_code`, `data_residency_required`, and `compliance_frameworks`. Passing a string like `"EU"` will fail validation.

---

**Q: How do I add automated checks for a new framework?**

Subclass `SovereignDeployer` and override `_checks_for_framework()`. Add a new `if "MY_FRAMEWORK" in upper_framework:` branch that calls your custom check method. This keeps the dispatch table extensible without modifying the base class.

---

**Q: Does `aumai-sovereignstack` make actual network calls or API calls?**

No. Every operation is purely local computation against the `DeploymentConfig` and `data_policies` dict you provide. There are no network calls, no external APIs, and no telemetry.

---

## Next Steps

- [API Reference](api-reference.md) — complete documentation of every class, method, and model field
- [Examples](../examples/quickstart.py) — runnable quickstart script
- [Contributing](../CONTRIBUTING.md) — how to submit improvements
- [Discord community](https://discord.gg/aumai) — questions and discussion
