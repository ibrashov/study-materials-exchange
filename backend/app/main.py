from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException
from .api.router import router
from .core.config import settings

app = FastAPI(title='Study Materials Exchange', version='0.2.0')
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_credentials=False, allow_methods=['GET', 'POST', 'PATCH', 'DELETE'],
                   allow_headers=['Content-Type', 'Authorization'])
app.include_router(router)

@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, headers=exc.headers,
                        content={'error': {'code': f'http_{exc.status_code}', 'message': str(exc.detail)}})

@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={'error': {
        'code': 'validation_error', 'message': 'Request validation failed'}})

@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    return JSONResponse(status_code=503, content={'error': {
        'code': 'http_503', 'message': 'Database unavailable; check configuration and migrations'}})

@app.exception_handler(OSError)
async def storage_error(request: Request, exc: OSError):
    return JSONResponse(status_code=503, content={'error': {
        'code': 'http_503', 'message': 'Storage unavailable'}})
