from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Task(BaseModel):
    id: str
    description: str
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
