from typing import Literal
from pydantic import BaseModel, Field


class IncidentCreate(BaseModel):
    node_id: int = Field(default=0, ge=0, le=9999)
    status: Literal["Emergencia", "Normal"] = "Emergencia"
    incident_text: str = Field(min_length=4, max_length=500)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
