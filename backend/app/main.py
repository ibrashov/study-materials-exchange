from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from .api.router import router
from .core.config import settings

app = FastAPI(title="Study Materials Exchange", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origins,
    allow_credentials=False, allow_methods=["GET"], allow_headers=["Content-Type"])
app.include_router(router)


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, headers=exc.headers,
                        content={"error": {"code": f"http_{exc.status_code}",
                                           "message": str(exc.detail)}})


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": {
        "code": "validation_error", "message": "Request validation failed"}})
