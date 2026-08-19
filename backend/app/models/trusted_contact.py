from pydantic import BaseModel


class TrustedContact(BaseModel):
    name: str
    phone_number: str


class TrustedContactUpdate(BaseModel):
    name: str | None = None
    phone_number: str | None = None
