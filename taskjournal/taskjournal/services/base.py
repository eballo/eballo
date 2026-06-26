from dataclasses import dataclass, field
from enum import Enum


class ServiceStatus(Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    UNCONFIGURED = "unconfigured"


@dataclass
class HealthCheckResult:
    status: ServiceStatus
    message: str
    details: list[str] = field(default_factory=list)


class BaseService:
    """
    Base class for all Task Journal services.

    Provides a common contract:
      - name: human-readable identifier used in logs and wk doctor output.
      - health_check: reports configuration and connectivity status.

    Services with external dependencies (Jira, GitHub, OpenAI, ...) should
    override health_check() to perform real validation. Pure utility services
    (FileService, TimeService, ...) inherit the default OK result.
    """

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(
            status=ServiceStatus.OK,
            message="Service available",
        )
