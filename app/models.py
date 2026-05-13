from pydantic import BaseModel, Field
from typing import Optional, List


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question")
    session_id: Optional[str] = None
    use_rag: bool = True
    top_k: int = 3


class AskResponse(BaseModel):
    answer: str
    sources: List[str] = []
    session_id: Optional[str] = None


class AgentRequest(BaseModel):
    task: str
    max_steps: int = 5


class AgentStep(BaseModel):
    thought: str
    action: str
    observation: str


class AgentResponse(BaseModel):
    final_answer: str
    steps: List[AgentStep] = []
