from fastapi import FastAPI
from app.routers.category import router as category_router
from app.routers.unit import router as unit_router  # Import the unit router
from app.routers.office import router as office_router  # Import the office router

app = FastAPI(
    title="Central Stock Management System",
    version="1.0.0"
)

app.include_router(category_router)
app.include_router(unit_router)  # Include the unit router
app.include_router(office_router)  # Include the office router
@app.get("/")
def home():
    return {
        "message": "Welcome to the Central Stock Management System API!"
    }
