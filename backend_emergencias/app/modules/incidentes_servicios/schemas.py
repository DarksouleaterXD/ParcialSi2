from pydantic import BaseModel


class IncidentesHealth(BaseModel):
    modulo: str
    status: str
