from pydantic import BaseModel


class PagosHealth(BaseModel):
    modulo: str
    status: str
