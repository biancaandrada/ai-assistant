from fastapi import APIRouter, Request

from ....controllers import DocumentsController
from ....schemas.documents import DeleteResponse, DocumentList

router = APIRouter()


@router.get("/documents", response_model=DocumentList)
async def list_documents(request: Request) -> DocumentList:
    ctrl: DocumentsController = request.app.state.documents_controller
    return await ctrl.list()


@router.delete("/documents/{source}", response_model=DeleteResponse)
async def delete_document(source: str, request: Request) -> DeleteResponse:
    ctrl: DocumentsController = request.app.state.documents_controller
    return await ctrl.delete(source)
