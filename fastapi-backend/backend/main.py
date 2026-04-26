from fastapi import FastAPI
from backend.database.db import engine, Base
from backend.routes.recruitment import router as recruitment_router
from backend.routes.approval import router as approval_router

# Create database tables automatically for this example
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Recruitment Backend API")

app.include_router(recruitment_router)
app.include_router(approval_router)

@app.get("/")
def read_root():
    return {"status": "running"}
