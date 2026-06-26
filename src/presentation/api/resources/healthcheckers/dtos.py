from pydantic import BaseModel

from src.application.healthcheckers.entity import HealthCheckReport


class LivezResponse(BaseModel):
    liveness: bool = True


class ReadyzResponse(HealthCheckReport):
    pass
