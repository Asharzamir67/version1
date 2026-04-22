from pydantic import BaseModel
from typing import List, Optional

class AdminCreate(BaseModel):
    username: str
    password: str

class AdminLogin(BaseModel):
    username: str
    password: str

class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

class ChatContextRequest(BaseModel):
    prompt: Optional[str] = "Summarize the current system status."
    history: Optional[List[ChatMessage]] = []
