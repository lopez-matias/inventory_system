from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR, get_settings
from app.exceptions import DomainError
from app.routers import dashboard, inventory, locations, movements, products


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    description="REST API for products, locations, inventory levels, and stock movements.",
    version="1.0.0",
    debug=settings.debug,
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")

api_prefix = "/api"
app.include_router(products.router, prefix=api_prefix)
app.include_router(locations.router, prefix=api_prefix)
app.include_router(inventory.router, prefix=api_prefix)
app.include_router(movements.router, prefix=api_prefix)
app.include_router(dashboard.router, prefix=api_prefix)


@app.exception_handler(DomainError)
async def domain_error_handler(_request: Request, exc: DomainError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "code": exc.code},
    )


@app.get("/api/health", tags=["System"])
def health_check():
    return {"status": "ok", "environment": settings.app_environment}


@app.get("/", include_in_schema=False)
def application_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"app_name": settings.app_name},
    )
