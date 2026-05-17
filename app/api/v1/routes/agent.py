from fastapi import APIRouter

from ....controllers import AgentController
from ....schemas.agent import AgentRequest, AgentResponse
from ...deps import AgentCtrlDep

router = APIRouter()


@router.post("/agent", response_model=AgentResponse)
async def agent(req: AgentRequest, ctrl: AgentController = AgentCtrlDep) -> AgentResponse:
    return await ctrl.handle(req)
