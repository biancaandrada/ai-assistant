from fastapi import APIRouter

from ....controllers import IndexController
from ....schemas.index import IndexRequest, IndexResponse
from ...deps import IndexCtrlDep

router = APIRouter()


@router.post("/index", response_model=IndexResponse)
async def index(req: IndexRequest, ctrl: IndexController = IndexCtrlDep) -> IndexResponse:
    return await ctrl.handle(req)
