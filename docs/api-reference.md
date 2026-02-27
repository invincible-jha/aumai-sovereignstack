# API Reference — aumai-sovereignstack

Complete reference for all public classes, functions, and Pydantic models.

---

## Module: `aumai_sovereignstack.core`

### `RegionNotFoundError`

```python
class RegionNotFoundError(KeyError)
```

Raised when a country code does not map to any registered region. Inherits from `KeyError`.

**Example:**

```python
from aumai_sovereignstack import RegionRegistry, RegionNotFoundError

registry = RegionRegistry()
try:
    registry.get_region("XX")
except RegionNotFoundError as exc:
    print(str(exc))  # "No region registered for country code 'XX'."
```

---

### `RegionRegistry`

```python
class RegionRegistry
```

Registry of sovereign regions. Pre-populated at construction time with five built-in regions: India (`IN`), European Union (`EU`), United States (`US`), Singapore (`SG`), and United Arab Emirates (`AE`).

Stores regions in a `dict[str, SovereignRegion]` keyed by uppercase ISO country code.

**Constructor:**

```python
RegionRegistry() -> None
```

Initializes the registry with all five pre-built regions.

---

#### `RegionRegistry.register_region`

```python
def register_region(self, region: SovereignRegion) -> None
```

Add or overwrite a region entry. The key is the region's `country_code` normalized to uppercase.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `region` | `SovereignRegion` | The region to register. |

**Returns:** `None`

**Example:**

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
```

---

#### `RegionRegistry.get_region`

```python
def get_region(self, country_code: str) -> SovereignRegion
```

Look up a region by its ISO 3166-1 alpha-2 country code.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `country_code` | `str` | ISO 3166-1 alpha-2 code (e.g. `"IN"`, `"EU"`, `"US"`, `"SG"`, `"AE"`). Case-insensitive — normalized to uppercase internally. |

**Returns:** `SovereignRegion`

**Raises:** `RegionNotFoundError` — if no region is registered for that code.

**Example:**

```python
eu = registry.get_region("EU")
print(eu.name)                      # "European Union"
print(eu.data_residency_required)   # True
print(eu.compliance_frameworks)     # ['GDPR', 'EU AI Act', 'NIS2 Directive']

# Case-insensitive
india = registry.get_region("in")   # equivalent to "IN"
```

---

#### `RegionRegistry.list_regions`

```python
def list_regions(self) -> list[SovereignRegion]
```

Return all registered regions sorted by `region_id` for deterministic output.

**Returns:** `list[SovereignRegion]`

**Example:**

```python
for region in registry.list_regions():
    residency = "required" if region.data_residency_required else "not required"
    print(f"[{region.country_code}] {region.name} — data residency {residency}")
```

---

### `SovereignDeployer`

```python
class SovereignDeployer
```

Orchestrates sovereign AI deployments with compliance validation. Stateless — every method is a pure function of its inputs.

**Constructor:**

```python
SovereignDeployer() -> None
```

---

#### `SovereignDeployer.create_config`

```python
def create_config(
    self,
    name: str,
    region: SovereignRegion,
    infrastructure: dict[str, object] | None = None,
    model_configs: list[dict[str, object]] | None = None,
    data_policies: dict[str, object] | None = None,
) -> DeploymentConfig
```

Build a new `DeploymentConfig` for the specified region.

A convenience factory that wraps `DeploymentConfig(...)` directly, providing `{}` and `[]` defaults for optional dicts and lists.

**Parameters:**

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | required | Human-readable deployment name. |
| `region` | `SovereignRegion` | required | The target sovereign region. |
| `infrastructure` | `dict[str, object] \| None` | `None` → `{}` | Key/value map of infrastructure properties (provider, data center, etc.). |
| `model_configs` | `list[dict[str, object]] \| None` | `None` → `[]` | Per-model configuration entries. |
| `data_policies` | `dict[str, object] \| None` | `None` → `{}` | Data handling policy rules. The primary input for automated compliance checks. |

**Returns:** `DeploymentConfig`

**Example:**

```python
from aumai_sovereignstack import RegionRegistry, SovereignDeployer

registry = RegionRegistry()
deployer = SovereignDeployer()

sg = registry.get_region("SG")
config = deployer.create_config(
    name="sg-recommender",
    region=sg,
    infrastructure={"provider": "aws", "region_zone": "ap-southeast-1"},
    model_configs=[{"model": "gpt-4o-mini", "max_tokens": 512}],
    data_policies={"purpose_limitation": "recommendation_only"},
)
```

---

#### `SovereignDeployer.validate_compliance`

```python
def validate_compliance(self, config: DeploymentConfig) -> list[ComplianceCheck]
```

Run all applicable compliance checks for a deployment configuration.

Always runs `check_data_residency()` first. Then iterates `config.region.compliance_frameworks` and dispatches each framework to a handler via substring matching on the uppercase framework name. Unknown frameworks produce a single passing "acknowledged" check.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `config` | `DeploymentConfig` | The deployment configuration to evaluate. |

**Returns:** `list[ComplianceCheck]` — all check results. Length varies by region and framework count.

**Example:**

```python
checks = deployer.validate_compliance(config)
passed = sum(1 for c in checks if c.passed)
failed = sum(1 for c in checks if not c.passed)
print(f"Checks: {len(checks)} total, {passed} passed, {failed} failed")
```

---

#### `SovereignDeployer.check_data_residency`

```python
def check_data_residency(self, config: DeploymentConfig) -> ComplianceCheck
```

Verify that the deployment satisfies the region's data residency requirement.

If `config.region.data_residency_required` is `False`, the check passes unconditionally. If `True`, `config.data_policies["data_residency"]` must be set to `True`.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `config` | `DeploymentConfig` | The deployment config to inspect. |

**Returns:** `ComplianceCheck` with `framework="Data Residency"`.

| Scenario | `passed` | `check_name` |
|---|---|---|
| Region does not require residency | `True` | `"data_residency_not_required"` |
| Region requires residency and policy is set | `True` | `"data_residency_enforced"` |
| Region requires residency and policy is missing/False | `False` | `"data_residency_enforced"` |

**Example:**

```python
check = deployer.check_data_residency(config)
print(check.passed)    # True or False
print(check.details)   # Human-readable explanation
```

---

#### `SovereignDeployer.generate_report`

```python
def generate_report(self, config: DeploymentConfig) -> DeploymentReport
```

Generate a full compliance report for the given deployment configuration.

Calls `validate_compliance()` internally, evaluates `all()` over the results, and packages everything into a `DeploymentReport`.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `config` | `DeploymentConfig` | The deployment configuration to evaluate. |

**Returns:** `DeploymentReport` with `all_compliant=True` only if every check passed.

**Example:**

```python
report = deployer.generate_report(config)

if report.all_compliant:
    print(f"Deployment '{report.config.name}' is fully compliant.")
else:
    for check in report.compliance_results:
        if not check.passed:
            print(f"FAILED: [{check.framework}] {check.check_name}")
            print(f"  {check.details}")
```

---

### Built-in Framework Check Details

`SovereignDeployer` dispatches compliance checks based on substrings found in the uppercase framework name. The following private methods implement the automated checks:

#### GDPR checks (`"GDPR"` in framework)

| Check name | Policy key | Passes when |
|---|---|---|
| `gdpr_dpo_designated` | `data_protection_officer` | value is truthy |
| `gdpr_lawful_basis_defined` | `lawful_basis` | value is truthy |

#### DPDP Act checks (`"DPDP"` in framework)

| Check name | Policy key / condition | Passes when |
|---|---|---|
| `dpdp_consent_mechanism` | `consent_mechanism` | value is truthy |
| `dpdp_data_fiduciary_in_india` | `config.region.country_code == "IN"` | deployment is in India region |

#### HIPAA checks (`"HIPAA"` in framework)

| Check name | Policy key | Passes when |
|---|---|---|
| `hipaa_phi_access_controls` | `phi_access_controls` | value is truthy |

#### PDPA checks (`"PDPA"` in framework)

| Check name | Policy key | Passes when |
|---|---|---|
| `pdpa_purpose_limitation` | `purpose_limitation` | value is truthy |

#### UAE checks (`"UAE PDPL"` or `"TDRA"` in framework)

| Check name | Policy key | Passes when |
|---|---|---|
| `uae_cross_border_transfer_controls` | `cross_border_transfer_controls` | value is truthy |

---

## Module: `aumai_sovereignstack.models`

### `SovereignRegion`

```python
class SovereignRegion(BaseModel)
```

Represents a national or organizational sovereign jurisdiction.

**Fields:**

| Field | Type | Required | Default | Constraints | Description |
|---|---|---|---|---|---|
| `region_id` | `str` | Yes | — | — | Unique identifier (e.g. `"in"`, `"eu"`). |
| `name` | `str` | Yes | — | — | Human-readable region name. |
| `country_code` | `str` | Yes | — | `min_length=2`, `max_length=3` | ISO 3166-1 alpha-2 or alpha-3 code. |
| `data_residency_required` | `bool` | No | `False` | — | Whether data must physically remain inside this region. |
| `compliance_frameworks` | `list[str]` | No | `[]` | — | Names of applicable compliance frameworks and laws. |

**Example:**

```python
from aumai_sovereignstack.models import SovereignRegion

brazil = SovereignRegion(
    region_id="br",
    name="Brazil",
    country_code="BR",
    data_residency_required=False,
    compliance_frameworks=["LGPD", "Marco Civil da Internet"],
)
```

---

### `DeploymentConfig`

```python
class DeploymentConfig(BaseModel)
```

Configuration for a sovereign AI deployment. The `data_policies` dictionary is the primary input for all automated compliance checks.

**Fields:**

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | `str` | Yes | — | Deployment name. |
| `region` | `SovereignRegion` | Yes | — | Target sovereign region (nested object, not a string). |
| `infrastructure` | `dict[str, object]` | No | `{}` | Key/value map describing infrastructure properties (e.g. `provider`, `data_center`). |
| `model_configs` | `list[dict[str, object]]` | No | `[]` | Per-model configuration entries (e.g. model name, quantization, serving engine). |
| `data_policies` | `dict[str, object]` | No | `{}` | Data handling policy rules. Keys drive automated compliance checks. |

**Compliance-relevant `data_policies` keys:**

| Key | Used by |
|---|---|
| `"data_residency"` | Data Residency check (must be `True`) |
| `"data_protection_officer"` | GDPR DPO check |
| `"lawful_basis"` | GDPR lawful basis check |
| `"consent_mechanism"` | DPDP Act consent check |
| `"phi_access_controls"` | HIPAA PHI check |
| `"purpose_limitation"` | PDPA purpose limitation check |
| `"cross_border_transfer_controls"` | UAE PDPL/TDRA check |

**Example:**

```python
from aumai_sovereignstack.models import DeploymentConfig, SovereignRegion

region = SovereignRegion(
    region_id="sg",
    name="Singapore",
    country_code="SG",
    data_residency_required=False,
    compliance_frameworks=["PDPA", "MAS TRM", "CSA Cybersecurity Act"],
)

config = DeploymentConfig(
    name="sg-fintech-ai",
    region=region,
    infrastructure={"provider": "gcp", "zone": "asia-southeast1"},
    model_configs=[{"model": "gemini-1.5-flash", "max_tokens": 2048}],
    data_policies={
        "purpose_limitation": "credit_risk_assessment",
    },
)

# Serialize for storage or transport
record = config.model_dump(mode="json")
restored = DeploymentConfig.model_validate(record)
```

---

### `ComplianceCheck`

```python
class ComplianceCheck(BaseModel)
```

Result of evaluating a single compliance rule.

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `check_name` | `str` | Yes | Machine-readable name of the check (e.g. `"gdpr_dpo_designated"`). |
| `passed` | `bool` | Yes | `True` if the check passed, `False` otherwise. |
| `details` | `str` | Yes | Human-readable explanation of the check result. |
| `framework` | `str` | Yes | Name of the compliance framework this check belongs to (e.g. `"GDPR"`, `"Data Residency"`). |

**Example:**

```python
from aumai_sovereignstack.models import ComplianceCheck

check = ComplianceCheck(
    check_name="gdpr_dpo_designated",
    passed=True,
    details="Data Protection Officer is designated.",
    framework="GDPR",
)
print(check.passed)    # True
print(check.details)   # "Data Protection Officer is designated."
```

---

### `DeploymentReport`

```python
class DeploymentReport(BaseModel)
```

Full compliance report for a deployment configuration. Produced by `SovereignDeployer.generate_report()`.

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `config` | `DeploymentConfig` | Yes | The evaluated deployment configuration. |
| `compliance_results` | `list[ComplianceCheck]` | No (default `[]`) | All individual compliance check results. |
| `all_compliant` | `bool` | Yes | `True` only if every check in `compliance_results` passed. |

**Example:**

```python
from aumai_sovereignstack.models import DeploymentReport

# Typically created by SovereignDeployer.generate_report(), not directly
report = deployer.generate_report(config)

print("Compliant:", report.all_compliant)
print("Checks run:", len(report.compliance_results))
print("Passed:", sum(1 for c in report.compliance_results if c.passed))
print("Failed:", sum(1 for c in report.compliance_results if not c.passed))

# Serialize the entire report
report_json = report.model_dump(mode="json")
```

---

## Module: `aumai_sovereignstack.cli`

The CLI is a Click group registered as the `aumai-sovereignstack` entry point. All commands use module-level singleton instances of `RegionRegistry` and `SovereignDeployer`.

### Commands summary

| Command | Description |
|---|---|
| `deploy --config PATH` | Generate human-readable compliance report; exits 1 on failure |
| `compliance --config PATH` | Run checks and emit JSON array; exits 1 on failure |
| `regions [--list] [--country CODE]` | List all regions or look up one by country code |

---

## Package exports (`aumai_sovereignstack.__init__`)

The following names are importable directly from `aumai_sovereignstack`:

```python
from aumai_sovereignstack import (
    ComplianceCheck,
    DeploymentConfig,
    DeploymentReport,
    RegionNotFoundError,
    RegionRegistry,
    SovereignDeployer,
    SovereignRegion,
)
```

Package version:

```python
import aumai_sovereignstack
print(aumai_sovereignstack.__version__)  # "0.1.0"
```
