from uuid import uuid4

import boto3
from fastapi import UploadFile

from app.core.config import get_settings


ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
}


def s3_client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
    )


def validate_upload(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Unsupported file type")


async def upload_document(tenant_id: str, file: UploadFile) -> tuple[str, str]:
    validate_upload(file)
    settings = get_settings()
    extension = (file.filename or "upload").split(".")[-1]
    object_key = f"{tenant_id}/documents/{uuid4()}.{extension}"
    body = await file.read()
    s3_client().put_object(Bucket=settings.s3_bucket, Key=object_key, Body=body, ContentType=file.content_type)
    return object_key, file.content_type or "application/octet-stream"
