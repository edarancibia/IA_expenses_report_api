from datetime import date
from typing import Optional
from fastapi import UploadFile, File, Form, APIRouter
from app.api.services.process_files import process_zip_file

api_router = APIRouter()

@api_router.post("/upload-zip/")
async def upload_zip(
    file: UploadFile = File(...),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None)
):
    zip_content = await file.read()

    start = date.fromisoformat(start_date) if start_date else None
    end = date.fromisoformat(end_date) if end_date else None

    result = process_zip_file(zip_content, start_date_input=start, end_date_input=end)

    return {
        "status": result["status"],
        "total_read_vouchers": result["total_read_vouchers"],
        "summary": result["summary"],
        "expenses": result["expenses"]
    }
    # if file.content_type != 'application/zip':
    #     return {"error": "El archivo debe ser un ZIP"}

    # zip_content = await file.read()

    # with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_file:
    #     file_list = zip_file.namelist()

    # return {"status": "Archivo ZIP recibido", "files": file_list}