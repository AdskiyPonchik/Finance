from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router, auth_router, users_router
from app.core.database import create_db_and_tables, engine
from app.core.models import User, Category, CategoryType
from app.core.auth import get_password_hash

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    with Session(engine) as session:
        # Check if admin user exists
        admin_user = session.exec(select(User).where(User.username == "admin")).first()
        if not admin_user:
            hashed_pw = get_password_hash("admin")
            admin_user = User(username="admin", hashed_password=hashed_pw)
            session.add(admin_user)
            session.commit()
            session.refresh(admin_user)
            print("(!) Admin user created: admin / admin")

            # Seed default categories only if the user is newly created
            default_categories = [
                Category(name="Groceries", type=CategoryType.EXPENSE, color="#4CAF50", owner_id=admin_user.id),
                Category(name="Rent", type=CategoryType.EXPENSE, color="#F44336", owner_id=admin_user.id),
                Category(name="Salary", type=CategoryType.INCOME, color="#FFC107", owner_id=admin_user.id),
                Category(name="Entertainment", type=CategoryType.EXPENSE, color="#9C27B0", owner_id=admin_user.id),
                Category(name="Transport", type=CategoryType.EXPENSE, color="#2196F3", owner_id=admin_user.id),
                Category(name="Savings", type=CategoryType.VAULT, color="#795548", owner_id=admin_user.id),
            ]
            session.add_all(default_categories)
            session.commit()
            print(f"(!) Seeded default categories for user 'admin'")
    yield

app = FastAPI(lifespan=lifespan)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# API Routers
app.include_router(auth_router, prefix="/api", tags=["Authentication"])
app.include_router(users_router, prefix="/api/users", tags=["Users"])
app.include_router(router, prefix="/api", tags=["Finance"])

# Root path to serve the frontend
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
