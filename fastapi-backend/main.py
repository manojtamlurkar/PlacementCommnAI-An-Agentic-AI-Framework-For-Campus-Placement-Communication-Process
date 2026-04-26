from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes import recruitment, approval
from backend.routes.email import router as email_router
from backend.routes.email_actions import router as email_actions_router
from backend.routes.company import router as company_router
from backend.routes.logistics import router as logistics_router
from backend.routes.activity import router as activity_router
from backend.routes.telegram_group import router as telegram_group_router
from backend.routes.spoc import router as spoc_router
from backend.database.db import engine, Base
from dotenv import load_dotenv
import os
from contextlib import asynccontextmanager
from backend.services.company_agent import start_agent_thread

load_dotenv()

# This line is crucial: it tells SQLAlchemy to create the tables in the DB
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start telegram polling thread for Company Agent
    start_agent_thread()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local dev
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(recruitment.router)
app.include_router(approval.router)
app.include_router(email_router)
app.include_router(email_actions_router)
app.include_router(company_router)
app.include_router(logistics_router)
app.include_router(activity_router)
app.include_router(telegram_group_router)
app.include_router(spoc_router)

@app.get("/")
def read_root():
    return {"status": "running"}