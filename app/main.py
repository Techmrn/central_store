from fastapi import FastAPI
from app.routers.category import router as category_router
from app.routers.unit import router as unit_router  # Import the unit router

app = FastAPI(
    title="Central Stock Management System",
    version="1.0.0"
)

app.include_router(category_router)
app.include_router(unit_router)  # Include the unit router

@app.get("/")
def home():
    return {
        "message": "Welcome to the Central Stock Management System API!"
    }
