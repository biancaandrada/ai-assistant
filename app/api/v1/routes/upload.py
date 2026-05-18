from fastapi import APIRouter, File, Request, UploadFile

from ....controllers import UploadController
from ....schemas.upload import UploadResponse

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload(request: Request, file: UploadFile = File(...)) -> UploadResponse:
    ctrl: UploadController = request.app.state.upload_controller
    data = await file.read()
    return await ctrl.handle_pdf(file.filename or "uploaded.pdf", data)
