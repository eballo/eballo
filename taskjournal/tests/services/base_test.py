from taskjournal.services.base import BaseService, HealthCheckResult, ServiceStatus


class TestBaseService:

    def test_default_name_returns_class_name(self) -> None:
        svc = BaseService()
        assert svc.name == "BaseService"

    def test_subclass_name_returns_subclass_name(self) -> None:
        class MyService(BaseService):
            pass

        svc = MyService()
        assert svc.name == "MyService"

    def test_default_health_check_returns_ok(self) -> None:
        svc = BaseService()
        result = svc.health_check()
        assert isinstance(result, HealthCheckResult)
        assert result.status == ServiceStatus.OK
        assert result.message == "Service available"
