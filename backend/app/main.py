from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from app.api.api_v1.api import api_router
from app.core.config import settings
from app.db import session, crud, models
from app.services.sheets_service import init_google_sheets

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Database Setup (Create tables if they don't exist)
models.Base.metadata.create_all(bind=session.engine)

@app.on_event("startup")
def on_startup():
    # Seed data
    db = session.SessionLocal()
    try:
        crud.init_db_data(db)
        # Init services
        init_google_sheets()
    finally:
        db.close()

# Include API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "Chatbot API is running"}
