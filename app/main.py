from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.api.routes import auth_router, router, users_router
from app.core.config import ROOT_DIR
from app.core.database import engine
from app.core.models import User

app = FastAPI(title="Finance", version="1.0.0")
# Browser and API share an origin; no permissive CORS middleware is needed.
app.mount("/static", StaticFiles(directory=ROOT_DIR / "app/static"), name="static")
templates = Jinja2Templates(directory=ROOT_DIR / "app/templates")
app.include_router(auth_router, prefix="/api", tags=["Authentication"])
app.include_router(users_router, prefix="/api/users", tags=["Users"])
app.include_router(router, prefix="/api", tags=["Finance"])


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    try:
        with Session(engine) as session:
            session.exec(select(User.id).limit(1)).all()
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database not ready")
    return {"status": "ok"}