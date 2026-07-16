from fastapi import FastAPI
from app.routers.category import router as category_router

app = FastAPI(
    title="Central Stock Management System",
    version="1.0.0"
)

app.include_router(category_router)

@app.get("/")
def home():
    return {
        "message": "Welcome to the Central Stock Management System API!"
    }
