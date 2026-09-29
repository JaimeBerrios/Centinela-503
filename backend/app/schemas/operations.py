from typing import Literal
from pydantic import BaseModel, Field

Role = Literal["admin", "coordinator", "brigade_operator", "reporter"]


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9._-]+$")
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=10, max_length=128)
    role: Role
    brigade_id: int | None = Field(default=None, gt=0)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    password: str | None = Field(default=None, min_length=10, max_length=128)
    role: Role | None = None
    brigade_id: int | None = Field(default=None, gt=0)
    active: bool | None = None


class BrigadeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    zone: str = Field(default="", max_length=120)
    skills: list[str] = Field(default_factory=list, max_length=12)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class BrigadeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    zone: str | None = Field(default=None, max_length=120)
    skills: list[str] | None = Field(default=None, max_length=12)
    status: Literal["Disponible", "Fuera de servicio"] | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class AssignmentCreate(BaseModel):
    incident_id: int = Field(gt=0)
    brigade_id: int = Field(gt=0)
    note: str = Field(default="", max_length=500)


class AssignmentUpdate(BaseModel):
    status: Literal["En camino", "Atendiendo", "Completada", "Cancelada"]
    details: str = Field(default="", max_length=500)


class IncidentUpdate(BaseModel):
    priority: Literal["Alta", "Media", "Baja", "Pendiente"] | None = None
    triage_state: Literal["Validada", "Rechazada", "Pendiente de validación"] | None = None
    resolution_status: Literal["Abierta", "Asignada", "En atención", "Resuelta", "Cancelada"] | None = None
    decision_note: str = Field(default="", max_length=500)


class DecisionCreate(BaseModel):
    incident_id: int | None = Field(default=None, gt=0)
    action: str = Field(min_length=2, max_length=120)
    details: str = Field(min_length=2, max_length=1000)


class PolicyUpdate(BaseModel):
    cluster_radius_m: int | None = Field(default=None, ge=10, le=500)
    simulator_enabled: bool | None = None
