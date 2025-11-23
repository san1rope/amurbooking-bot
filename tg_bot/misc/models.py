from typing import Optional, Any
from datetime import datetime

from pydantic import BaseModel


class BookingSlot(BaseModel):
    dateBooked: datetime
    availableToBook: bool


class WorkTypes:
    BOOKING_PROCESSING = "booking_processing"
    GET_TRUCKS_LIST = "get_trucks_list"


class QueueMessage(BaseModel):
    msg_type: str
    data: Any = None


class ProxyData(BaseModel):
    host: str
    port: str
    username: Optional[str] = None
    password: Optional[str] = None
    available: bool = True
    current_task: int = 0

    def __str__(self):
        return f"{self.host}:{self.port}:{self.username}:{self.password}"
