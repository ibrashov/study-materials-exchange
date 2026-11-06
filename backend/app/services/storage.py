from pathlib import Path
from uuid import uuid4
from fastapi import HTTPException, UploadFile
from pypdf import PdfReader
from ..core.config import MAX_FILE_BYTES, settings

CHUNK_BYTES = 1024 * 1024

def validate_pdf(path):
    try:
        with path.open('rb') as source:
            if source.read(5) != b'%PDF-':
                raise ValueError('Missing PDF header')
            source.seek(0)
            pdf = PdfReader(source, strict=True)
            if pdf.is_encrypted or len(pdf.pages) == 0:
                raise ValueError('Empty or encrypted PDF')
    except Exception:
        raise HTTPException(415, 'Upload a readable, unencrypted PDF with at least one page') from None

def save_pdf(upload: UploadFile):
    directory = settings.uploads_dir.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    name = uuid4().hex + '.pdf'
    temporary = directory / (name + '.part')
    final = directory / name
    try:
        size = 0
        with temporary.open('xb') as output:
            while chunk := upload.file.read(CHUNK_BYTES):
                size += len(chunk)
                if size > MAX_FILE_BYTES:
                    raise HTTPException(413, 'File exceeds 52428800 bytes')
                output.write(chunk)
        if size == 0:
            raise HTTPException(422, 'File is empty')
        validate_pdf(temporary)
        temporary.replace(final)
        return name, size
    except BaseException:
        temporary.unlink(missing_ok=True)
        final.unlink(missing_ok=True)
        raise

def stored_path(name: str) -> Path:
    directory = settings.uploads_dir.resolve()
    candidate = (directory / name).resolve()
    if candidate.parent != directory or candidate.suffix != '.pdf':
        raise HTTPException(404, 'File not found')
    return candidate
