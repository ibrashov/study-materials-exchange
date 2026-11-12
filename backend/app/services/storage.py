from pathlib import Path
from uuid import uuid4
import logging
import tempfile
import httpx
from fastapi import HTTPException, UploadFile
from pypdf import PdfReader
from ..core.config import MAX_FILE_BYTES, settings

CHUNK_BYTES = 1024 * 1024
logger = logging.getLogger(__name__)

def cloud_request(method, name, **kwargs):
    if settings.storage_backend != 'supabase' or not settings.supabase_url.startswith('https://') or not settings.supabase_service_role_key:
        logger.warning('Cloud configuration: backend=%s url_valid=%s key_present=%s',
                       settings.storage_backend, settings.supabase_url.startswith('https://'), bool(settings.supabase_service_role_key))
        raise HTTPException(503, 'Cloud storage is not configured')
    if len(name) != 36 or not name.endswith('.pdf') or any(c not in '0123456789abcdef' for c in name[:-4]):
        raise HTTPException(404, 'File not found')
    url = f'{settings.supabase_url.rstrip("/")}/storage/v1/object/{settings.supabase_bucket}/{name}'
    try:
        response = httpx.request(method, url, headers={
            'Authorization': f'Bearer {settings.supabase_service_role_key}',
            'apikey': settings.supabase_service_role_key,
            'Content-Type': 'application/pdf',
        }, timeout=90, **kwargs)
    except httpx.RequestError as exc:
        logger.warning('Cloud storage connection failed: %s', type(exc).__name__)
        raise HTTPException(503, 'Storage unavailable') from None
    if response.status_code == 404:
        raise HTTPException(404, 'File not found')
    if not response.is_success:
        logger.warning('Cloud storage returned HTTP %s for %s', response.status_code, method)
        raise HTTPException(503, 'Storage unavailable')
    return response

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
    if settings.storage_backend == 'supabase':
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'upload.pdf'
            size = 0
            with path.open('wb') as output:
                while chunk := upload.file.read(CHUNK_BYTES):
                    size += len(chunk)
                    if size > MAX_FILE_BYTES:
                        raise HTTPException(413, 'File exceeds 52428800 bytes')
                    output.write(chunk)
            if not size:
                raise HTTPException(422, 'File is empty')
            validate_pdf(path)
            name = uuid4().hex + '.pdf'
            with path.open('rb') as source:
                cloud_request('POST', name, content=source.read())
            return name, size
    if settings.storage_backend != 'local':
        raise HTTPException(503, 'Storage is not configured')
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

def remove_stored(name: str):
    """Best effort after commit; a file left behind is listed by the storage check."""
    try:
        if settings.storage_backend == 'supabase':
            cloud_request('DELETE', name)
        else:
            stored_path(name).unlink(missing_ok=True)
    except (HTTPException, OSError):
        logger.warning('Failed to remove stored object %s', name)

def download_stored(name: str):
    if settings.storage_backend == 'supabase':
        return cloud_request('GET', name).content
    path = stored_path(name)
    if not path.is_file():
        raise HTTPException(404, 'File not found')
    return path
