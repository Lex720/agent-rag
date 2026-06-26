from dataclasses import dataclass
from typing import List


@dataclass
class CheckResult:
    name: str
    passed: bool
    details: str | None = None


@dataclass
class HealthCheckReport:
    healthy: bool
    checks: List[CheckResult]
