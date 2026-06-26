import asyncio
from operator import attrgetter
from typing import List

from src.application.healthcheckers.entity import CheckResult, HealthCheckReport
from src.application.healthcheckers.interface import CheckRepository, CheckUsecase


class Check(CheckUsecase):
    def __init__(self, check_repository: CheckRepository, name: str) -> None:
        self.__check_repository = check_repository
        self.__name = name

    async def __call__(self) -> CheckResult:
        try:
            await self.__check_repository()
            return CheckResult(name=self.__name, passed=True)
        except Exception as ex:
            return CheckResult(name=self.__name, passed=False, details=str(ex))


class HealthCheck:
    def __init__(self, healthcheckers: List[Check]) -> None:
        self.__healthcheckers = healthcheckers

    async def __call__(self) -> HealthCheckReport:
        results = await asyncio.gather(*[check() for check in self.__healthcheckers])
        return HealthCheckReport(
            healthy=all(map(attrgetter("passed"), results)),
            checks=list(results),
        )
