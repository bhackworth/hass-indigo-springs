"""Sample data from Indigo Springs devices."""

from pydantic import BaseModel


class Sample(BaseModel):
    """A single measurement from one of the Indigo Springs devices."""

    sn: str
    temperature: float = None
    humidity: float = None
    moisture: float = None
    voltage: int = None
    battery: float = None
    solar: int = None
    sw: str = None
    hw: str = None
