from pydantic import BaseModel


class TallerTecnicoHealth(BaseModel):
    modulo: str
    status: str
