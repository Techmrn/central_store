from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers.category import router as category_router
from app.routers.unit import router as unit_router  # Import the unit router
from app.routers.office import router as office_router  # Import the office router
from app.routers.section import router as section_router 
from app.routers.financial_year import router as financial_year_router
from app.routers.item import router as item_router
from app.routers.opening_stock import router as opening_stock_router

#importing jinja templates
from app.routers.ui import dashboard   # Including HTML Template 
from app.routers.ui import category

app = FastAPI(
    title="Central Stock Management System",
    version="1.0.0"
)

app.include_router(category_router)
app.include_router(unit_router)  # Include the unit router
app.include_router(office_router)  # Include the office router
app.include_router(section_router) # Include the sections router
app.include_router(financial_year_router)
app.include_router(item_router)
app.include_router(opening_stock_router)
app.include_router(dashboard.router)
app.include_router(category.router)

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)


# @app.get("/")
# def home():
#     return {
#         "message": "Welcome to the Central Stock Management System API!"
#     }
