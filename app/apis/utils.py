from datetime import datetime

from pydantic import BaseModel


class HTTPError(BaseModel):
    detail: str


class TotalAndMonthAmount(BaseModel):
    month: int
    total: int
    last_checked: datetime
