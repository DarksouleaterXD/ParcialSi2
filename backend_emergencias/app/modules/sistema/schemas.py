from pydantic import BaseModel


class ModuloSistemaHealth(BaseModel):
    modulo: str
    status: str
