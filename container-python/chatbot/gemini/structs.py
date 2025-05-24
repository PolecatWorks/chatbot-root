from typing import List
from pydantic import BaseModel



class Part(BaseModel):
    text: str

class Content(BaseModel):
    parts: List[Part]

class GeminiRequest(BaseModel):
    contents: List[Content]
