from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException
from .api.router import router
from .core.config import settings
from .services.ratelimit import limiter, match_rule

app = FastAPI(title='Study Materials Exchange', version='0.2.0')


@app.middleware('http')
async def rate_limit(request: Request, call_next):
    # Registered before CORS so that 429 responses still carry CORS headers.
    if settings.rate_limit_enabled and request.method != 'OPTIONS' and request.url.path.startswith('/api/'):
        client = request.client.host if request.client else 'unknown'
        if settings.trust_proxy_headers and request.headers.get('x-forwarded-for'):
            client = request.headers['x-forwarded-for'].split(',')[0].strip()
        allowed, retry_after = limiter.check(client, match_rule(request.method, request.url.path))
        if not allowed:
            return JSONResponse(status_code=429, headers={'Retry-After': str(retry_after)}, content={'error': {
                'code': 'http_429', 'message': f'Too many requests. Try again in {retry_after} seconds.'}})
    return await call_next(request)

app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_credentials=False, allow_methods=['GET', 'POST', 'PATCH', 'DELETE'],
                   allow_headers=['Content-Type', 'Authorization'], expose_headers=['Retry-After'])
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
