
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers.category import router as category_router
from app.routers.unit import router as unit_router  # Import the unit router
from app.routers.office import router as office_router  # Import the office router
from app.routers.section import router as section_router 
from app.routers.financial_year import router as financial_year_router
from app.routers.item import router as item_router
from app.routers.opening_stock import router as opening_stock_router
from app.routers.role import router as role_router
from app.routers.user import router as user_router
from app.routers.permission import router as permission_router
from app.routers.role_permission import router as role_permission_router
from app.routers.user_role import router as user_role_router
from app.routers.login_history import router as login_history_router
from app.routers.auth import router as auth_router # for user authentication and JWT generation
from app.routers.asset import router as asset_router
from app.routers.indent import router as indent_router
from app.routers.issue import router as issue_router
from app.routers.receipt import router as receipt_router
from app.routers.stock_return import router as stock_return_router
from app.routers.transfer import router as transfer_router
from app.routers.outward_pass import router as outward_pass_router
from app.routers.stock import router as stock_router
from app.routers.unserviceable import router as unserviceable_router



#importing jinja templates
from app.routers.ui import dashboard   # Including HTML Template 
from app.routers.ui import auth as ui_auth
from app.routers.ui import category
from app.routers.ui import unit
from app.routers.ui import office
from app.routers.ui import section
from app.routers.ui import item
from app.routers.ui import financial_year
from app.routers.ui import role
from app.routers.ui import user
from app.routers.ui import permission
from app.routers.ui import role_permission
from app.routers.ui import user_role
from app.routers.ui import login_history
from app.routers.ui import opening_stock as opening_stock_ui
from app.routers.ui import unserviceable as unserviceable_ui
from app.routers.ui import indent as indent_ui
from app.routers.ui import issue as issue_ui
from app.routers.ui import receipt as receipt_ui
from app.routers.ui import stock_return as stock_return_ui
from app.routers.ui import transfer as transfer_ui
from app.routers.ui import stock as stock_ui





app = FastAPI(
    title="Central Stock Management System",
    version="1.0.0"
)

# UI routers
app.include_router(ui_auth.router)
app.include_router(dashboard.router) #ui router
app.include_router(indent_ui.router) # indent UI router
app.include_router(issue_ui.router) # issue UI router
app.include_router(receipt_ui.router) # receipt UI router
app.include_router(stock_return_ui.router) # stock return UI router
app.include_router(transfer_ui.router) # transfer UI router
app.include_router(category.router) #ui router
app.include_router(unit.router) # adding ui of unit master
app.include_router(office.router) # adding ui of office master
app.include_router(section.router) # adding ui of Section master
app.include_router(item.router) # adding ui of Items master
app.include_router(financial_year.router) # adding ui of financial year master
app.include_router(role.router) # adding ui of role master
app.include_router(user.router) # adding ui of user master
app.include_router(permission.router) # adding ui of permission master
app.include_router(role_permission.router)
app.include_router(user_role.router)
app.include_router(login_history.router)
app.include_router(opening_stock_ui.router)
app.include_router(unserviceable_ui.router)
app.include_router(stock_ui.router)

# REST API routers
app.include_router(category_router)
app.include_router(unit_router)  # Include the unit router
app.include_router(office_router)  # Include the office router
app.include_router(section_router) # Include the sections router
app.include_router(financial_year_router)
app.include_router(item_router)
app.include_router(opening_stock_router)
app.include_router(role_router)
app.include_router(user_router)
app.include_router(permission_router)
app.include_router(role_permission_router)
app.include_router(user_role_router)
app.include_router(login_history_router)
app.include_router(auth_router) # auth router
app.include_router(asset_router)
app.include_router(indent_router)
app.include_router(issue_router)
app.include_router(receipt_router)
app.include_router(stock_return_router)
app.include_router(transfer_router)

app.include_router(outward_pass_router)
app.include_router(stock_router)
app.include_router(unserviceable_router)





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
