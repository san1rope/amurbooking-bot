from typing import Any, Optional

from pydantic import BaseModel


class ProxyData(BaseModel):
    id: int
    host: str
    port: str
    username: Optional[str] = None
    password: Optional[str] = None
    available: bool = True

    def __str__(self):
        return f"{self.host}:{self.port}:{self.username}:{self.password}"
