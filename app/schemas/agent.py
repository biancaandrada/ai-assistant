from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    task: str = Field(..., min_length=1, max_length=4000)
    max_steps: int = Field(5, ge=1, le=20)


class AgentStep(BaseModel):
    thought: str
    action: str
    observation: str


class AgentResponse(BaseModel):
    final_answer: str
    steps: list[AgentStep] = []
