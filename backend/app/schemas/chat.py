from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    message: str
    history: List[str]

class ChatResponse(BaseModel):
    reply: str
    order_placed: bool = False
