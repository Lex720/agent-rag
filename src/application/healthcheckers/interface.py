from abc import ABC, abstractmethod

from src.application.healthcheckers.entity import CheckResult


class CheckRepository(ABC):
    @abstractmethod
    async def __call__(self) -> bool: ...


class CheckUsecase(ABC):
    @abstractmethod
    async def __call__(self) -> CheckResult: ...
