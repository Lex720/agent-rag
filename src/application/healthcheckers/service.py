from src.application.healthcheckers.usecase import Check as CheckUseCase
from src.application.healthcheckers.usecase import HealthCheck as HealthCheckUseCase
from src.infrastructure.healthcheckers.postgres import Check as CheckRepositoryPostgres


def postgres_check() -> CheckUseCase:
    return CheckUseCase(CheckRepositoryPostgres(), "PostgreSQL")


def health_check() -> HealthCheckUseCase:
    return HealthCheckUseCase([postgres_check()])
