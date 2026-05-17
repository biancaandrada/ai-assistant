from fastapi import APIRouter

from ....controllers import AskController
from ....schemas.ask import AskRequest, AskResponse
from ...deps import AskCtrlDep

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest, ctrl: AskController = AskCtrlDep) -> AskResponse:
    return await ctrl.handle(req)
