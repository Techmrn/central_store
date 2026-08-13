# Central Store ERP - Full Technical Analysis

**Project:** Central Stock Management System  
**Stack:** FastAPI, SQLAlchemy 2.x, PostgreSQL, Jinja2, Alembic  
**Architecture:** Monolith with dual-interface (REST API + Server-Side Rendered HTML)  
**Analysed on:** 2026-08-13

---

## Table of Contents

1. Business Context
2. Full Project Structure
3. Technology Stack and Dependencies
4. Database Model Catalog
5. Enum Reference
6. Business Flow
7. Authentication and Authorization Flow
8. Module-by-Module File Flow from Login
   - 8.1 Auth / Login
   - 8.2 Dashboard
   - 8.3 Master Data Modules
   - 8.4 Opening Stock
   - 8.5 Indent (Physical Indent)
   - 8.6 Issue
   - 8.7 Receipt
   - 8.8 Stock Return
   - 8.9 Stock Transfer
   - 8.10 Outward Pass
   - 8.11 Asset Management
   - 8.12 Unserviceable Material
   - 8.13 Stock / Reports
9. Core Service Layer Flows
10. Posting Service - Transaction Lifecycle
11. Permission System Architecture
12. Modules Completed vs To Be Implemented
13. Identified Flaws and Risks

---

## 1. Business Context

The system is built for the **Government Printing Department** which operates:

```
Government Printing Department
|
+-- Directorate
|
+-- Central Store  (Central Press campus - this system primary actor)
|       |
|       +-- Supplies Directorate Sections
|       +-- Supplies Central Press Sections
|       +-- Transfers stock to all Branch Offices
|
+-- Branch Office 1 -> Branch Store
+-- Branch Office 2 -> Branch Store
+-- ...
```

**The Central Store** manages:
- Procurement and Receipt of goods from suppliers
- Issue of consumable materials and assets to offices/sections
- Inter-office stock transfers
- Asset lifecycle: register, issue, transfer, return, unserviceable, condemnation
- Indent (requisition) management from requesting offices
- Comprehensive stock ledger and reporting registers

---

## 2. Full Project Structure

```
central_store/
|
+-- .env                              <- DB URL, SECRET_KEY, ALGORITHM, TOKEN_EXPIRE
+-- .gitignore
+-- alembic.ini                       <- Alembic migration config
+-- requirements.txt                  <- Root requirements (UTF-16 encoding issue)
+-- seed_permissions.py               <- Standalone permission seeder script
+-- store architechture.txt           <- Architecture design notes
+-- indent structure.txt              <- Indent workflow design notes
+-- Central_Store_ERP V1_Final_Design_Reference.md
+-- UI_Authorization_Architecture_Study.pdf
|
+-- alembic/
|   +-- env.py                        <- Migration environment
|   +-- script.py.mako
|   +-- versions/                     <- Migration version files
|
+-- tests/                            <- Directory exists; zero tests written
|
+-- app/
    +-- main.py                       <- FastAPI app factory; all 47 router registrations
    +-- requirements.txt              <- Pinned Python dependencies (UTF-8 encoded)
    |
    +-- core/
    |   +-- config.py                 <- Reads .env: DATABASE_URL, SECRET_KEY, ALGORITHM
    |   +-- db.py                     <- SQLAlchemy engine + SessionLocal + get_db()
    |   +-- security.py               <- Argon2 password hash/verify + JWT create/decode
    |   +-- templates.py              <- Jinja2Templates instance
    |   +-- pagination.py             <- Reusable paginator helper
    |   +-- constants.py              <- PAGE_SIZE = 20
    |
    +-- models/                       <- 25+ SQLAlchemy ORM model files
    |   +-- base.py                   <- BaseModel: id, created_at, updated_at, is_active
    |   +-- enums.py                  <- 10 enum classes
    |   +-- __init__.py               <- Exports all models (needed for Alembic)
    |   +-- [25 model files: see section 4]
    |
    +-- schemas/                      <- Pydantic v2 request/response validation
    |   +-- [24 schema files matching model names]
    |
    +-- crud/                         <- Data-access layer: all DB queries
    |   +-- [22 crud files]
    |
    +-- services/                     <- Business-logic layer
    |   +-- auth_service.py           <- authenticate_user()
    |   +-- permission_service.py     <- get_user_permissions(), has_permission()
    |   +-- permission_seed.py        <- seed_permissions(), seed_admin_permissions()
    |   +-- posting_service.py        <- post_issue/receipt/return/transfer() (398 lines)
    |   +-- stock_service.py          <- get_item_stock/usable_stock/validate()
    |   +-- document_number_service.py <- generate_document_number() PREFIX-YYYY-XXXX
    |
    +-- dependencies/
    |   +-- auth.py                   <- get_current_user() Bearer JWT for REST
    |   +-- ui_auth.py                <- get_current_user_ui() HttpOnly cookie for UI
    |   +-- permissions.py            <- require_permission() / require_permission_ui()
    |
    +-- routers/
    |   +-- [23 REST API router files]
    |   |
    |   +-- ui/                       <- HTML-returning routers (Jinja2 templates)
    |       +-- auth.py               <- GET/POST /login, GET /logout
    |       +-- dashboard.py          <- GET /dashboard, GET / (redirect)
    |       +-- [15 additional UI router files]
    |
    +-- static/                       <- CSS, JS, images
    |
    +-- templates/                    <- Jinja2 HTML templates (20 sub-directories)
```

---

## 3. Technology Stack and Dependencies

| Layer | Technology | Version |
|---|---|---|
| Web Framework | FastAPI | 0.139.0 |
| ASGI Server | Uvicorn | 0.51.0 |
| ORM | SQLAlchemy | 2.0.51 |
| Database | PostgreSQL | psycopg2-binary 2.9.12 |
| Migrations | Alembic | 1.18.5 |
| Data Validation | Pydantic v2 | 2.13.4 |
| Templating | Jinja2 via Starlette | - |
| Password Hashing | pwdlib Argon2 | - |
| JWT | PyJWT | - |
| Config | python-dotenv | 1.2.2 |

**Security model:**
- REST API: Bearer JWT in Authorization header
- UI browser: HttpOnly cookie named access_token (SameSite=lax)

---

## 4. Database Model Catalog

### BaseModel (inherited by every table)
- id (Integer, PK, auto-increment)
- created_at (DateTime with timezone, server_default=now())
- updated_at (DateTime with timezone, onupdate=now())
- is_active (Boolean, default=True) - soft delete flag

### Master Data Tables

| Table | Model Class | Key Fields |
|---|---|---|
| categories | Category | code, name, type (Material/Asset enum) |
| units | Unit | code, name |
| offices | Office | code, name |
| sections | Section | code, name, office_id FK |
| financial_years | FinancialYear | year_name, start_date, end_date, is_current |
| items | Item | code, name, category_id FK, unit_id FK |
| opening_stocks | OpeningStock | item_id FK, office_id FK, financial_year_id FK, quantity, unit_rate |

### User and Access Control Tables

| Table | Model Class | Key Fields |
|---|---|---|
| users | User | code(7 chars), username(50), password_hash, full_name, office_id FK, section_id FK, email, mobile, last_login |
| roles | Role | code, name |
| permissions | Permission | code (MODULE_ACTION), module, action, name, description |
| role_permissions | RolePermission | role_id FK, permission_id FK |
| user_roles | UserRole | user_id FK, role_id FK |
| login_history | LoginHistory | user_id FK, login_time, logout_time, ip_address, user_agent, status |

### Asset Tables

| Table | Model Class | Key Fields |
|---|---|---|
| assets | Asset | asset_no (unique), item_id FK, serial_no (unique nullable), office_id FK, section_id FK, status (AssetStatus enum), remarks |
| asset_details | AssetDetail | asset_id FK (1:1), make, model, year_of_purchase, and additional specs |
| asset_movements | AssetMovement | asset_id FK, movement_type (AssetMovementType enum), from_office_id FK, from_section_id FK, to_office_id FK, to_section_id FK, reference_document, movement_date |

### Transaction Tables

| Table | Model Class | Key Fields |
|---|---|---|
| indents | Indent | indent_no, indent_date, received_date, financial_year_id, office_id, section_id, request_source, status (IndentStatus), reference_no, created_by_id, processed_by_id, closed_by_id |
| indent_lines | IndentLine | indent_id FK, item_id FK, requested_quantity, issued_quantity, remarks |
| issues | Issue | issue_no (unique), issue_date, financial_year_id, indent_id FK, office_id, section_id, destination_type, status (TransactionStatus), created_by_id, posted_by_id, posted_at |
| issue_lines | IssueLine | issue_id FK, item_id FK, unit_id FK, quantity, remarks |
| issue_line_assets | IssueLineAsset | issue_line_id FK, asset_id FK |
| receipts | Receipt | receipt_no (unique), receipt_date, financial_year_id, office_id, section_id, supplier_name, reference_no, status, created_by_id, posted_by_id |
| receipt_lines | ReceiptLine | receipt_id FK, item_id FK, unit_id FK, quantity, unit_price, remarks |
| stock_returns | StockReturn | return_no (unique), return_date, financial_year_id, office_id, section_id, reference_issue_id FK (optional), status, created_by_id, posted_by_id |
| stock_return_lines | StockReturnLine | return_id FK, item_id FK, unit_id FK, quantity, remarks |
| stock_return_line_assets | StockReturnLineAsset | return_line_id FK, asset_id FK |
| stock_transfers | StockTransfer | transfer_no (unique), transfer_date, financial_year_id, from_office_id FK, from_section_id FK, to_office_id FK, to_section_id FK, status, created_by_id, posted_by_id |
| stock_transfer_lines | StockTransferLine | transfer_id FK, item_id FK, unit_id FK, quantity, remarks |
| stock_transfer_line_assets | StockTransferLineAsset | transfer_line_id FK, asset_id FK |
| outward_passes | OutwardPass | issue_id FK (1:1), pass_date, purpose, recipient_name, destination, vehicle_details, remarks |
| unserviceable_materials | UnserviceableMaterial | financial_year_id FK, item_id FK, office_id FK, section_id FK, quantity, reason, status (UnserviceableStatus), date_reported, reference_no, reported_by_id FK |

### Central Ledger Table

| Table | Model Class | Purpose |
|---|---|---|
| stock_movements | StockMovement | Central stock ledger: item_id, office_id, movement_type, transaction_source, quantity_in, quantity_out, movement_date, reference_type, reference_id, reference_no |

---

## 5. Enum Reference

```
Category_Type
  MATERIAL | ASSET

AssetStatus
  IN_STORE | ISSUED | UNDER_REPAIR | DAMAGED | CONDEMNED | E_WASTE | DISPOSED

AssetMovementType
  RECEIPT | ISSUE | TRANSFER | RETURN | UNSERVICEABLE | REPAIR | CONDEMNATION | DISPOSAL

UnserviceableStatus
  UNSERVICEABLE | UNDER_REPAIR | REPAIRED | CONDEMNED | DISPOSED

IndentStatus
  DRAFT | PROCESSING | CLOSED | SUBMITTED | OFFICE_APPROVED | HEAD_OFFICE_APPROVED | SENT_TO_STORE | REJECTED

RequestSource
  PHYSICAL | ONLINE

TransactionStatus
  DRAFT | POSTED | CANCELLED

MovementType
  OPENING | RECEIPT | ISSUE | RETURN | TRANSFER_IN | TRANSFER_OUT | ADJUSTMENT_IN | ADJUSTMENT_OUT

TransactionSource
  OPENING | HISTORICAL | OPERATIONAL

DestinationType
  INTERNAL | EXTERNAL
```

---

## 6. Business Flow

```
MASTER DATA SETUP
  Create: Financial Year -> Category -> Unit -> Office -> Section -> Item -> Opening Stock

USER AND ACCESS SETUP
  Create: Roles -> Assign Permissions to Roles -> Create Users -> Assign Roles to Users

INDENT LIFECYCLE
  Requesting Office creates physical Indent (paper form)
       |
  Storekeeper receives and records it in system (indent_no entered from printed form)
       |
  Status: DRAFT (or SUBMITTED if online future)
       |
  Storekeeper reviews: enters issued quantities per line
  Status: PROCESSING
       |
  Path A (Single-step, immediate): Submit directly
    -> auto-creates Issue document
    -> auto-posts Issue (stock deducted, assets moved, indent closed)
    -> Redirect to printable Receipt page

  Path B (Two-step, deferred): Save as pending
    -> Storekeeper saves issued quantities
    -> Later creates Issue separately from indent detail page
    -> Reviews Issue draft
    -> Posts Issue

  On Issue POST (atomic transaction):
    1. Validate stock availability (usable stock >= issued qty)
    2. Validate asset count and status (IN_STORE) for asset items
    3. Create StockMovement(ISSUE, quantity_out) per line
    4. Create AssetMovement(ISSUE) + update Asset status/location per asset
    5. Update IndentLine.issued_quantity
    6. Set Indent.status -> CLOSED
    7. Set Issue.status -> POSTED

RECEIPT LIFECYCLE (Goods Received from Suppliers)
  Create Receipt header (supplier, reference, date)
  Add lines (item, qty, unit_price)
  Review draft
  POST -> StockMovement(RECEIPT, quantity_in) per line -> Receipt POSTED

STOCK RETURN LIFECYCLE
  Create Return (optional reference to original issue)
  Add lines (item, qty) and assets for asset items
  POST -> StockMovement(RETURN, quantity_in) + Asset->IN_STORE -> Return POSTED

STOCK TRANSFER LIFECYCLE (Inter-office)
  Create Transfer (from_office -> to_office)
  Add lines (item, qty) and assets for asset items
  POST -> StockMovement(TRANSFER_OUT) at from_office
       -> StockMovement(TRANSFER_IN) at to_office
       -> Asset location updated to to_office
       -> Transfer POSTED

OUTWARD PASS (for external deliveries)
  Created on/after Issue POST for EXTERNAL destination_type issues
  Records: purpose, recipient, destination, vehicle details

UNSERVICEABLE MATERIAL
  Record items declared unserviceable with quantity and reason
  Status lifecycle: UNSERVICEABLE -> UNDER_REPAIR -> REPAIRED / CONDEMNED / DISPOSED

STOCK CALCULATION FORMULA
  Physical Stock = OpeningStock.quantity (if no OPENING StockMovement exists)
                 + SUM(StockMovement.quantity_in - StockMovement.quantity_out)
                   WHERE NOT HISTORICAL source
  Usable Stock   = max(0, Physical Stock - Active Unserviceable Quantity)
  (Active unserviceable = status IN [UNSERVICEABLE, UNDER_REPAIR])
```

---

## 7. Authentication and Authorization Flow

### REST API Authentication (Bearer Token)

```
Client Request
    |
    Authorization: Bearer <JWT>
    |
dependencies/auth.py -> get_current_user()
    |
    credentials = HTTPBearer()(request)
    token = credentials.credentials
    |
core/security.py -> decode_access_token(token)
    jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    |
    user_id = payload["sub"]
    |
DB: SELECT * FROM users WHERE id=user_id AND is_active=True
    |
Return User object OR raise HTTP 401
```

### UI Browser Authentication (HttpOnly Cookie)

```
Browser Request
    |
    Cookie: access_token=<JWT>  [HttpOnly, SameSite=lax]
    |
dependencies/ui_auth.py -> get_current_user_ui()
    |
    token = request.cookies.get("access_token")
    If no token: raise HTTP 303 -> redirect /login
    |
core/security.py -> decode_access_token(token)
    |
    user_id = payload["sub"]
    |
DB: SELECT * FROM users WHERE id=user_id AND is_active=True
    If None: raise HTTP 303 -> redirect /login
    |
services/permission_service.py -> get_user_permissions(db, user.id)
    user.perm_codes = {p.code for p in perms}   [attached to user object]
    |
Return User object
```

### Permission Enforcement

```
Permission Code format: MODULE_ACTION  (uppercase, spaces->underscores)
Examples: INDENT_CREATE, ISSUE_POST, STOCK_VIEW, USER_ROLE_ASSIGN

REST API:   @router.get("/", current_user=Depends(require_permission("INDENT_VIEW")))
            -> require_permission(code) creates dependency:
               get_current_user() -> has_permission(db, user_id, code)

UI Routes:  current_user=Depends(get_current_user_ui)   [no permission on most UI routes]
            Some routes use require_permission_ui(code) for enforcement

has_permission(db, user_id, permission_code):
  1. get_user_roles(user_id)
     -> SELECT user_roles JOIN roles WHERE user_id AND is_active
  2. For each role: get_permissions_by_role(role_id)
     -> SELECT role_permissions JOIN permissions WHERE role_id AND is_active
  3. Deduplicate by code (use dict)
  4. Return any(p.code.upper() == permission_code.upper())

NOTE: perm_codes set attached to user object by get_current_user_ui() is
      NEVER used for enforcement checks - has_permission() re-queries DB each time.
```

---

## 8. Module-by-Module File Flow from Login

### 8.1 Auth / Login

**UI Browser Flow:**
```
Step 1: GET /login
  routers/ui/auth.py -> login_page()
  -> templates/auth/login.html  [renders login form]

Step 2: POST /login  (form data: username, password)
  routers/ui/auth.py -> login_submit(username, password, db)
  -> services/auth_service.py -> authenticate_user(db, username, password, ip, user_agent)
     -> crud/user.py -> get_user_by_username(db, username)
        SELECT * FROM users WHERE username=? AND is_active=True
     -> If user is None: raise ValueError("Invalid username or password")
     -> core/security.py -> verify_password(password, user.password_hash)
        password_hash.verify() [Argon2]
     -> If fails: raise ValueError("Invalid username or password")
     -> crud/login_history.py -> create_login_history(db, LoginHistoryCreate)
        INSERT INTO login_history (user_id, login_time, ip_address, user_agent, status="SUCCESS")
     -> core/security.py -> create_access_token(data={"sub": str(user.id)})
        jwt.encode({sub, exp}, SECRET_KEY, algorithm=HS256)
     <- Returns dict {access_token, token_type, user, login_history_id}
  <- Response: RedirectResponse(url="/dashboard", status_code=303)
     Set-Cookie: access_token=<JWT>; HttpOnly; SameSite=lax
  [On ValueError]: Re-render login.html with error="Invalid username or password"

Step 3: GET /logout
  routers/ui/auth.py -> logout(request, db)
  -> request.cookies.get("access_token")
  -> core/security.py -> decode_access_token(token)
  -> DB: find active LoginHistory (logout_time IS NULL) for user_id, order by login_time DESC
  -> crud/login_history.py -> record_logout(db, history.id)
     UPDATE login_history SET logout_time=now() WHERE id=?
  -> RedirectResponse(url="/login", 303)
     delete_cookie("access_token")
```

**REST API Flow:**
```
POST /auth/login  Body: {username, password}
  routers/auth.py -> login(data, request, db)
  -> services/auth_service.py -> authenticate_user() [same as above]
  <- 200: {access_token, token_type:"bearer", user: UserRead, login_history_id}
  [On ValueError] <- 401: {detail: error message}

GET /auth/me  Header: Authorization: Bearer <token>
  routers/auth.py -> get_me(current_user=Depends(get_current_user))
  dependencies/auth.py -> get_current_user():
    HTTPBearer() extracts token
    decode_access_token(token)
    SELECT user WHERE id=sub AND is_active=True
  <- 200: UserRead

POST /auth/logout  Body: {login_history_id}  Header: Bearer <token>
  routers/auth.py -> logout(data, current_user, db)
  -> crud/login_history.py -> get_login_history_for_user(db, history_id, user_id)
  -> crud/login_history.py -> record_logout(db, history_id)
  <- 200: {message: "Logout recorded successfully."}
```

---

### 8.2 Dashboard

```
GET /dashboard  (requires cookie auth)
  routers/ui/dashboard.py -> dashboard(request, db, current_user)
  -> dependencies/ui_auth.py -> get_current_user_ui()
     [validates cookie, attaches perm_codes to user]
  -> Direct inline DB queries:
     COUNT(items) WHERE is_active
     COUNT(indents) WHERE status IN [DRAFT, SUBMITTED, PROCESSING]
     COUNT(indents) WHERE status IN [SUBMITTED, PROCESSING]  [actionable]
     COUNT(issues) WHERE is_active
     COUNT(assets) WHERE is_active
     COUNT(unserviceable_materials) WHERE is_active
     SELECT issues ORDER BY created_at DESC LIMIT 5  [joinedload office, indent]
     SELECT indents ORDER BY created_at DESC LIMIT 5  [joinedload office]
  -> templates/dashboard/home.html
     Context: all counts + recent_issues + recent_indents + current_user

GET /  (root)
  routers/ui/dashboard.py -> root_redirect()
  -> RedirectResponse(url="/dashboard", 303)
```

---

### 8.3 Master Data Modules

All 12 master data modules follow an identical architectural pattern.
Using Category as representative example:

```
GET /categories  (list page)
  routers/ui/category.py
  -> dependencies/ui_auth.py -> get_current_user_ui()
  -> crud/category.py -> get_all_categories(db, search, page)
     SELECT categories WHERE is_active [+ ILIKE search] ORDER BY name LIMIT/OFFSET
  -> templates/category/list.html

GET /categories/new  (create form)
  routers/ui/category.py
  -> templates/category/form.html  [empty form]

POST /categories/new  (save)
  routers/ui/category.py
  -> crud/category.py -> create_category(db, CategoryCreate)
     Validate duplicates -> INSERT INTO categories
  -> RedirectResponse(/categories?success=...) OR re-render with error

GET /categories/{id}/edit  (edit form)
  -> crud/category.py -> get_category_by_id(db, id)
  -> templates/category/form.html  [pre-filled]

POST /categories/{id}/edit  (update)
  -> crud/category.py -> update_category(db, id, CategoryUpdate)
  -> RedirectResponse or error

POST /categories/{id}/delete  (soft delete)
  -> crud/category.py -> delete_category(db, id)
     UPDATE categories SET is_active=False WHERE id=?
  -> RedirectResponse

REST API equivalents (all permission-protected):
  POST   /categories/     requires CATEGORY_CREATE
  GET    /categories/     requires CATEGORY_VIEW
  GET    /categories/{id} requires CATEGORY_VIEW
  PUT    /categories/{id} requires CATEGORY_UPDATE
  DELETE /categories/{id} requires CATEGORY_DELETE
```

**Modules using this identical pattern:**
Category, Unit, Office, Section, FinancialYear, Item, Role, User,
Permission, RolePermission, UserRole, LoginHistory (view-only)

---

### 8.4 Opening Stock

```
GET /opening-stock/  (list with search + pagination)
  routers/ui/opening_stock.py -> list_opening_stocks(request, search, page, db, current_user)
  -> crud/opening_stock.py -> get_all_opening_stocks(db)
     SELECT ALL opening_stocks [no server-side filter]  [FLAW: loads all into memory]
  -> _filter_and_paginate_opening_stocks(all_stocks, search, page)
     [Python-side filtering by item name/code, FY name, office name]
  -> templates/opening_stock/list.html

GET /opening-stock/table  (AJAX partial for live search)
  -> Same data fetch, renders: templates/opening_stock/table_container.html

GET /opening-stock/new  (create form)
  -> financial_years list + items list loaded
  -> templates/opening_stock/form.html

POST /opening-stock/new
  -> OpeningStockCreate(financial_year_id, item_id, quantity, unit_rate)
  -> office_id implicitly = current_user.office_id  [FLAW: no override option]
  -> crud/opening_stock.py -> create_opening_stock(db, schema)
  -> RedirectResponse(/opening-stock/?success=...) or error re-render

GET /opening-stock/{id}/edit
  -> crud/opening_stock.py -> get_opening_stock_by_id(db, id)
  -> templates/opening_stock/form.html [pre-filled, is_edit=True]

POST /opening-stock/{id}/edit
  -> crud/opening_stock.py -> update_opening_stock(db, id, OpeningStockUpdate)
  -> RedirectResponse or error

POST /opening-stock/{id}/delete
  -> crud/opening_stock.py -> delete_opening_stock(db, id)
  -> RedirectResponse
```

---

### 8.5 Indent (Physical Indent - Core Operational Module)

This is the most complex UI module (592 lines).

```
GET /indents  OR  GET /indents/  (list with multiple filters)
  routers/ui/indent.py -> list_indents_ui(...)
  -> crud/indent.py -> get_all_indents(db, search, indent_no, fy_id, office_id, section_id, status, request_source, page)
     Builds SQLAlchemy query with optional WHERE clauses + pagination
  -> Loads: all offices, all sections, all financial years for filter dropdowns
  -> templates/indents/list.html

GET /indents/entry  OR  GET /indents/record  (new physical indent entry form)
  routers/ui/indent.py -> record_physical_indent_ui(...)
  -> Loads: offices, sections, active items list
  -> templates/indents/entry.html

POST /indents/entry  (process new indent form submission)
  routers/ui/indent.py -> submit_physical_indent_ui(request, db, current_user)

  Step 1: Read multipart form data (async)
    indent_no, indent_date, office_id, section_id, reference_no, remarks, action_type
    item_id[] , requested_qty[], issued_qty[], line_remarks[]  (parallel arrays)

  Step 2: Validation
    - indent_no required
    - Parse dates and IDs (raise redirect on parse error)
    - get_current_financial_year(db) [financial_years WHERE is_current=True]
    - Fallback: get first active financial_year if no current set
    - If no FY: error redirect

  Step 3: Duplicate check
    SELECT indents WHERE office_id=? AND fy_id=? AND LOWER(indent_no)=? AND is_active=True
    If exists AND CLOSED: redirect error "already completed"
    If exists AND pending: redirect to existing record view

  Step 4: Parse line items
    For each item_id in array:
      - Parse req_qty (must be > 0) and iss_qty (0 <= iss_qty <= req_qty)
      - For ASSET category items: query IN_STORE assets, auto-assign up to iss_qty
        (FLAW: .limit(iss_qty) without order, non-deterministic assignment)

  Step 5: Create Indent
    crud/indent.py -> create_indent(db, IndentCreate, user_id)

  If action_type == "save":
    -> RedirectResponse /indents?success=...

  If action_type == "submit":
    -> crud/issue.py -> create_issue(db, IssueCreate{lines}, user_id)
    -> services/posting_service.py -> post_issue(db, issue.id, user_id)
       [See section 10 for full posting flow]
    -> RedirectResponse /indents/receipt/{indent.id}

GET /indents/receipt/{indent_id}  (printable receipt view)
  -> crud/indent.py -> get_indent_by_id(db, id)
  -> SELECT issues WHERE indent_id=? AND is_active=True  [get linked issue]
  -> templates/indents/receipt.html

GET /indents/view/{indent_id}  OR  GET /indents/{indent_id}  (detail view)
  -> crud/indent.py -> get_indent_by_id(db, id)
  -> For each active IndentLine:
       services/stock_service.py -> get_item_usable_stock(db, item_id, office_id)
       services/stock_service.py -> get_item_stock(db, item_id, office_id)
       services/stock_service.py -> get_item_unserviceable_stock(db, item_id, office_id)
       Determine is_asset: item.category.type == ASSET
  -> templates/indents/detail.html
     Context: indent, enriched_lines[{line, usable_stock, physical_stock, unserviceable_stock, is_asset}]

POST /indents/{indent_id}/process  (edit saved pending indent)
  -> Read form: issued_qty_{line.id}, remarks_{line.id} per line
  -> Validate: iss_qty >= 0, iss_qty <= line.requested_quantity
  -> For asset items: auto-assign IN_STORE assets (same FLAW as entry)
  -> crud/indent.py -> update_indent(db, id, IndentUpdate{lines, status=PROCESSING}, user_id)
  If save:   -> redirect to view
  If submit: -> create_issue() -> post_issue() -> redirect receipt

POST /indents/{indent_id}/close  (manual close without issue)
  -> crud/indent.py -> close_indent(db, id, user_id)
     UPDATE indents SET status=CLOSED, closed_by_id=?, closed_at=now() WHERE id=?
  -> RedirectResponse /indents/view/{id}?success=...

REST API:
  POST   /indents/           INDENT_CREATE permission
  GET    /indents/           INDENT_VIEW permission
  GET    /indents/{id}       INDENT_VIEW permission
  PUT    /indents/{id}       INDENT_UPDATE permission
  DELETE /indents/{id}       INDENT_DELETE permission
  POST   /indents/{id}/close INDENT_CLOSE permission
```

---

### 8.6 Issue

```
GET /issues  OR  /issues/  (list with filters)
  routers/ui/issue.py -> list_issues_ui(...)
  -> crud/issue.py -> get_all_issues(db, search, issue_no, fy_id, office_id, section_id, status, page)
  -> Load: offices, sections, financial_years for dropdowns
  -> templates/issues/list.html

GET /issues/create?indent_id={id}  (create issue form pre-loaded from Indent)
  routers/ui/issue.py -> create_issue_form_ui(indent_id, ...)
  -> crud/indent.py -> get_indent_by_id(db, indent_id)
  -> services/document_number_service.py -> generate_document_number(db, Issue, "issue_no", "ISS", fy_id)
     [Generates next ISS-2026-XXXX number]
  -> For each active IndentLine:
       services/stock_service.py -> get_item_usable_stock(db, item_id, indent.office_id)
       If ASSET: query Asset WHERE item_id=? AND office_id=? AND status=IN_STORE
       default_qty = line.issued_quantity if > 0 else line.requested_quantity
  -> templates/issues/create.html
     Context: indent, proposed_issue_no, prepared_lines [{line, default_qty, usable_stock, is_asset, available_assets}]

POST /issues/create
  routers/ui/issue.py -> submit_create_issue_ui(request, db, current_user)
  -> Parse: indent_id, fy_id, office_id, section_id, destination_type, reference_no
  -> For each indent line with qty > 0:
       qty_{line.id}, remarks_{line.id}, assets_{line.id}[] from form
       For ASSET: validate len(selected_asset_ids) == int(qty_val)
       Build IssueLineCreate list
  -> crud/issue.py -> create_issue(db, IssueCreate{...lines}, user_id)
     Generates issue_no via document_number_service
     INSERT INTO issues + INSERT INTO issue_lines + INSERT INTO issue_line_assets
  -> RedirectResponse /issues/{issue.id}/review?success=...

GET /issues/{id}/review  (review draft before posting)
  -> crud/issue.py -> get_issue_by_id(db, id)
  -> crud/outward_pass.py -> get_outward_pass_by_issue_id(db, issue.id)
  -> Calculate: total_lines, total_qty
  -> templates/issues/review.html

POST /issues/{id}/post  (post the issue - irreversible)
  -> services/posting_service.py -> post_issue(db, issue_id, user_id)
     [Full atomic transaction - see section 10]
  -> On success: templates/issues/posted.html
  -> On ValueError: RedirectResponse review?error=...

POST /issues/{id}/outward-pass  (generate outward gate pass)
  -> Parse: purpose, recipient, destination, vehicle_details, remarks
  -> crud/outward_pass.py -> create_outward_pass(db, OutwardPassCreate, user_id)
  -> RedirectResponse /issues/{id}/review

REST API:
  POST   /issues/          ISSUE_CREATE
  GET    /issues/          ISSUE_VIEW
  GET    /issues/{id}      ISSUE_VIEW
  PUT    /issues/{id}      ISSUE_UPDATE
  DELETE /issues/{id}      ISSUE_DELETE
  POST   /issues/{id}/post ISSUE_POST
```

---

### 8.7 Receipt

```
REST API only - NO HTML UI registered in main.py

routers/receipt.py (all endpoints permission-protected):
  POST   /receipts/           RECEIPT_CREATE
  GET    /receipts/           RECEIPT_VIEW   (paginated list with filters)
  GET    /receipts/{id}       RECEIPT_VIEW
  PUT    /receipts/{id}       RECEIPT_UPDATE
  DELETE /receipts/{id}       RECEIPT_DELETE
  POST   /receipts/{id}/post  RECEIPT_POST
    -> services/posting_service.py -> post_receipt(db, receipt_id, user_id)
       [See section 10 for details]
```

---

### 8.8 Stock Return

```
REST API only - NO HTML UI registered in main.py

routers/stock_return.py:
  POST   /returns/           RETURN_CREATE
  GET    /returns/           RETURN_VIEW
  GET    /returns/{id}       RETURN_VIEW
  POST   /returns/{id}/post  RETURN_POST
    -> services/posting_service.py -> post_return(db, return_id, user_id)
       [See section 10 for details]
```

---

### 8.9 Stock Transfer

```
REST API only - NO HTML UI registered in main.py

routers/transfer.py:
  POST   /transfers/           TRANSFER_CREATE
  GET    /transfers/           TRANSFER_VIEW
  GET    /transfers/{id}       TRANSFER_VIEW
  POST   /transfers/{id}/post  TRANSFER_POST
    -> services/posting_service.py -> post_transfer(db, transfer_id, user_id)
       [See section 10 for details]
```

---

### 8.10 Outward Pass

```
REST API only - no standalone UI

routers/outward_pass.py:
  POST   /outward-passes/     OUTWARD_PASS_CREATE
  GET    /outward-passes/     OUTWARD_PASS_VIEW
  GET    /outward-passes/{id} OUTWARD_PASS_VIEW

UI creation path: POST /issues/{id}/outward-pass in issue.py UI router
```

---

### 8.11 Asset Management

```
REST API only - NO HTML UI registered

routers/asset.py:
  POST   /assets/    ASSET_CREATE
  GET    /assets/    ASSET_VIEW   (list with filters: item, office, status, serial_no)
  GET    /assets/{id} ASSET_VIEW
  PUT    /assets/{id} ASSET_UPDATE
  DELETE /assets/{id} ASSET_DELETE

Asset is automatically updated (status, location) during:
  post_issue()    -> ISSUED, moved to receiving office
  post_return()   -> IN_STORE, moved back to store
  post_transfer() -> location updated to to_office

Asset movement history: asset_movements table
Asset extended specs: asset_details table (1:1 with asset)
```

---

### 8.12 Unserviceable Material

```
UI: View-only register
  GET /unserviceable-register  OR  /unserviceable-register/
  routers/ui/unserviceable.py -> get_unserviceable_register_ui(...)
  -> crud/unserviceable.py -> get_unserviceable_register_report(db, filters, page)
  -> templates/unserviceable_register/list.html
  Filters: asset_or_material, status_filter

REST API (full lifecycle):
  POST   /unserviceable/            UNSERVICEABLE_CREATE  (record unserviceable)
  GET    /unserviceable/            UNSERVICEABLE_VIEW
  GET    /unserviceable/{id}        UNSERVICEABLE_VIEW
  PUT    /unserviceable/{id}/status UNSERVICEABLE_UPDATE  (advance status)
```

---

### 8.13 Stock and Reports

```
REST API only - NO HTML UI templates exist

All endpoints require STOCK_VIEW permission:

GET /stock/balance  (current stock levels)
  -> crud/stock.py -> get_stock_balances(db, search, category_id, office_id, page)
  Returns: {item_code, item_name, category, unit, office, physical_stock, usable_stock}

GET /stock/ledger  (movement ledger)
  -> crud/stock.py -> get_stock_ledger(db, item_id, office_id, fy_id, page)
  Returns: StockMovement records in chronological order with running balance

GET /stock/distribution-register  (issue distribution report)
  -> crud/stock.py -> get_distribution_register(db, fy_id, office_id, section_id, item_id, page)
  Returns: All issues grouped/filterable by various dimensions

GET /stock/item-transaction-register?item_id=X
  -> crud/stock.py -> get_item_transaction_register(db, item_id, office_id, page)
  Returns: Full transaction history for specific item

GET /stock/asset-register
  -> crud/stock.py -> get_asset_register_report(db, item_id, office_id, section_id, status, page)

GET /stock/computer-register
  -> crud/stock.py -> get_computer_register_report(db, office_id, page)

GET /stock/e-waste-register
  -> crud/stock.py -> get_ewaste_register_report(db, office_id, page)

GET /stock/unserviceable-register
  -> crud/unserviceable.py -> get_unserviceable_register_report(db, filters, page)
  Multi-filter: fy, office, section, item, category, asset_or_material, status
```

---

## 9. Core Service Layer Flows

### services/stock_service.py

```
get_item_stock(db, item_id, office_id=None):
  STEP 1: Query StockMovement ledger
    SELECT SUM(quantity_in - quantity_out) FROM stock_movements
    WHERE item_id=? AND is_active=True AND transaction_source != 'HISTORICAL'
    [+ office_id filter if provided]
    movement_balance = result or 0.0

  STEP 2: Opening stock deduplication check
    Check if any StockMovement of type OPENING exists for item+office
    If YES: opening_balance = 0 (already included in movement_balance)
    If NO:
      SELECT SUM(quantity) FROM opening_stocks
      WHERE item_id=? AND is_active=True [+ office filter]
      opening_balance = result or 0.0

  STEP 3: Return round(opening_balance + movement_balance, 2)

get_item_unserviceable_stock(db, item_id, office_id=None):
  SELECT SUM(quantity) FROM unserviceable_materials
  WHERE item_id=? AND is_active=True
  AND status IN ('UNSERVICEABLE', 'UNDER_REPAIR')
  [+ office filter]
  Return round(result, 2)

get_item_usable_stock(db, item_id, office_id=None):
  physical = get_item_stock(db, item_id, office_id)
  unserviceable = get_item_unserviceable_stock(db, item_id, office_id)
  Return round(max(0.0, physical - unserviceable), 2)

validate_stock_availability(db, item_id, office_id, required_qty):
  usable = get_item_usable_stock(db, item_id, office_id)
  If usable < required_qty:
    physical = get_item_stock(...)
    unserviceable = get_item_unserviceable_stock(...)
    raise ValueError(
      f"Insufficient stock for item ID {item_id}. "
      f"Usable: {usable} (Physical: {physical}, Unserviceable: {unserviceable}), "
      f"Requested: {required_qty}."
    )
  Return True
```

### services/document_number_service.py

```
generate_document_number(db, model_class, number_field_name, prefix, financial_year_id):
  Format produced: PREFIX-YYYY-XXXX  (e.g. ISS-2026-0001)

  1. Query FinancialYear by financial_year_id
     Extract year: fy.year_name.split("-")[0].strip()
     Fallback: year_str = "2026"  [FLAW: hardcoded]

  2. Build pattern: "PREFIX-YYYY-%"
     field_attr = getattr(model_class, number_field_name)

  3. Query: SELECT field_attr FROM model WHERE field_attr LIKE pattern
            ORDER BY field_attr DESC LIMIT 1

  4. Parse: seq = int(last_doc.split("-")[-1]) + 1
            Fallback seq = 1 if parse fails or no docs

  5. Return f"{prefix}-{year_str}-{seq:04d}"

  FLAW: Race condition - two concurrent requests can read same seq and generate duplicates
```

### services/permission_service.py

```
get_user_roles(db, user_id):
  -> crud/user_role.py -> get_roles_by_user(db, user_id)
     SELECT roles FROM user_roles JOIN roles
     WHERE user_id=? AND user_roles.is_active=True AND roles.is_active=True

get_user_permissions(db, user_id):
  roles = get_user_roles(db, user_id)
  permissions = {}  # dict keyed by code for deduplication
  For each role:
    -> crud/role_permission.py -> get_permissions_by_role(db, role_id)
       SELECT permissions FROM role_permissions JOIN permissions
       WHERE role_id=? AND role_permissions.is_active=True
    For each perm:
      permissions[perm.code] = perm
  Return list(permissions.values())

has_permission(db, user_id, permission_code):
  permission_code = permission_code.strip().upper()
  permissions = get_user_permissions(db, user_id)
  Return any(p.code.upper() == permission_code for p in permissions)

NOTE: This hits the DB on EVERY permission check:
  - 1 query to get user_roles
  - N queries to get permissions per role
  Total = 1 + N queries per secured endpoint
```

### services/permission_seed.py

```
seed_permissions(db):
  Iterates PERMISSIONS list of 60+ tuples: (module, action, description)
  code = f"{module}_{action}".upper().replace(" ", "_")
  If Permission with code doesn't exist: create it
  Returns count of new records created

seed_admin_permissions(db):
  Finds Roles WHERE code IN ['ADMIN','STOREKEEPER','CENTRAL_STORE_KEEPER','STORE_KEEPER']
  If none found: uses first active role
  For each role: assign all 60+ permissions via create_role_permission()
  Skips if mapping already exists
  Returns count of new mappings created
```

---

## 10. Posting Service - Transaction Lifecycle

### post_issue() - Most Complex (atomic multi-table transaction)

```
post_issue(db, issue_id, user_id):

  === PRE-VALIDATION PHASE ===
  [No DB writes yet - fail fast before any changes]

  1. Load Issue: SELECT WHERE id=issue_id AND is_active=True
     If not found: raise ValueError
     If POSTED: raise ValueError("already posted")
     If CANCELLED: raise ValueError("cannot post cancelled")

  2. Load linked Indent: SELECT WHERE id=issue.indent_id AND is_active=True
     If not found: raise ValueError
     If Indent.status == CLOSED: raise ValueError("indent already closed")

  3. Check issue.lines: if empty raise ValueError

  4. For each IssueLine:
     a. item = line.item [lazy loaded]
        If not item: raise ValueError

     b. If item.category.type == ASSET:
        line_assets = [la.asset for la in line.assets if la.asset and la.asset.is_active]
        If len(line_assets) != int(line.quantity):
          raise ValueError("Selected assets count must match issue quantity")
        For each asset in line_assets:
          If asset.id already in selected_asset_ids: raise ValueError (duplicate)
          selected_asset_ids.add(asset.id)
          If asset.status != IN_STORE: raise ValueError("not IN_STORE")
          If asset.item_id != line.item_id: raise ValueError("wrong item")

     c. validate_stock_availability(db, line.item_id, indent.office_id, line.quantity)
        [Raises ValueError if usable stock insufficient]

  === ATOMIC EXECUTION PHASE ===
  try:
    For each IssueLine:
      1. Create StockMovement:
           financial_year_id = issue.financial_year_id
           item_id = line.item_id
           office_id = indent.office_id  [stock deducted from STORE office]
           section_id = indent.section_id
           movement_type = ISSUE
           quantity_in = 0.0
           quantity_out = line.quantity
           movement_date = func.now()
           reference_type = "ISSUE"
           reference_id = issue.id
           reference_no = issue.issue_no
         db.add(sm)

      2. For each IssueLineAsset:
           asset = line_asset.asset
           from_office_id = asset.office_id  [capture current location]
           from_section_id = asset.section_id
           asset.status = ISSUED
           asset.office_id = issue.office_id   [move to requesting office]
           asset.section_id = issue.section_id
           Create AssetMovement:
             asset_id, movement_type=ISSUE
             from_office_id/from_section_id
             to_office_id=issue.office_id, to_section_id=issue.section_id
             reference_document=issue.issue_no
             movement_date=func.now()
           db.add(am)

      3. Find IndentLine matching line.item_id:
           indent_line.issued_quantity = line.quantity

    4. indent.status = CLOSED
       indent.closed_by_id = user_id
       indent.closed_at = func.now()

    5. issue.status = POSTED
       issue.posted_by_id = user_id
       issue.posted_at = func.now()

    db.commit()
    db.refresh(issue)
    return issue

  except Exception:
    db.rollback()
    raise
```

### post_receipt()

```
post_receipt(db, receipt_id, user_id):
  Validate: exists AND is_active AND DRAFT AND has lines
  try:
    For each ReceiptLine:
      Create StockMovement:
        office_id = receipt.office_id
        movement_type = RECEIPT
        quantity_in = line.quantity
        quantity_out = 0.0
        reference_type = "RECEIPT"
    receipt.status = POSTED; posted_by_id; posted_at
    db.commit()
  except: db.rollback(); raise
```

### post_return()

```
post_return(db, return_id, user_id):
  Validate: exists AND DRAFT AND has lines
  try:
    For each StockReturnLine:
      1. Create StockMovement(RETURN, quantity_in=line.quantity, quantity_out=0)
      2. For each StockReturnLineAsset:
           capture current asset location
           asset.status = IN_STORE
           asset.office_id = stock_return.office_id
           asset.section_id = stock_return.section_id
           Create AssetMovement(RETURN, from->return office)
    stock_return.status = POSTED
    db.commit()
  except: db.rollback(); raise
```

### post_transfer()

```
post_transfer(db, transfer_id, user_id):
  Validate: exists AND DRAFT AND has lines
  For each line: validate_stock_availability(from_office_id, item_id, qty)
  try:
    For each StockTransferLine:
      1. StockMovement(TRANSFER_OUT, qty_out=line.qty, office=from_office)
      2. StockMovement(TRANSFER_IN, qty_in=line.qty, office=to_office)
      3. For each StockTransferLineAsset:
           asset.office_id = to_office_id
           asset.section_id = to_section_id
           Create AssetMovement(TRANSFER, from->to)
    transfer.status = POSTED
    db.commit()
  except: db.rollback(); raise
```

---

## 11. Permission System Architecture

```
Permission Code Format: {MODULE}_{ACTION}   (uppercase, spaces become underscores)

60+ Defined Permission Codes (examples):
  CATEGORY_VIEW, CATEGORY_CREATE, CATEGORY_UPDATE, CATEGORY_DELETE
  UNIT_VIEW, UNIT_CREATE, UNIT_UPDATE, UNIT_DELETE
  OFFICE_VIEW, OFFICE_CREATE, OFFICE_UPDATE, OFFICE_DELETE
  SECTION_VIEW, SECTION_CREATE, SECTION_UPDATE, SECTION_DELETE
  FINANCIAL_YEAR_VIEW, FINANCIAL_YEAR_CREATE, FINANCIAL_YEAR_UPDATE, FINANCIAL_YEAR_DELETE
  ITEM_VIEW, ITEM_CREATE, ITEM_UPDATE, ITEM_DELETE
  OPENING_STOCK_VIEW, OPENING_STOCK_CREATE, OPENING_STOCK_UPDATE, OPENING_STOCK_DELETE
  USER_VIEW, USER_CREATE, USER_UPDATE, USER_DELETE
  ROLE_VIEW, ROLE_CREATE, ROLE_UPDATE, ROLE_DELETE
  PERMISSION_VIEW, PERMISSION_CREATE, PERMISSION_UPDATE, PERMISSION_DELETE
  USER_ROLE_VIEW, USER_ROLE_ASSIGN, USER_ROLE_REMOVE
  ROLE_PERMISSION_VIEW, ROLE_PERMISSION_ASSIGN, ROLE_PERMISSION_REMOVE
  LOGIN_HISTORY_VIEW
  ASSET_VIEW, ASSET_CREATE, ASSET_UPDATE, ASSET_DELETE
  ASSET_MOVEMENT_VIEW, ASSET_MOVEMENT_CREATE
  INDENT_VIEW, INDENT_CREATE, INDENT_UPDATE, INDENT_DELETE, INDENT_CLOSE
  ISSUE_VIEW, ISSUE_CREATE, ISSUE_UPDATE, ISSUE_DELETE, ISSUE_POST
  RECEIPT_VIEW, RECEIPT_CREATE, RECEIPT_UPDATE, RECEIPT_DELETE, RECEIPT_POST
  RETURN_VIEW, RETURN_CREATE, RETURN_POST
  TRANSFER_VIEW, TRANSFER_CREATE, TRANSFER_POST
  STOCK_VIEW, STOCK_ADJUST
  OUTWARD_PASS_VIEW, OUTWARD_PASS_CREATE
  UNSERVICEABLE_VIEW, UNSERVICEABLE_CREATE, UNSERVICEABLE_UPDATE

Relational Graph:
  User --[user_roles]--> UserRole --[role_id]--> Role
       --[role_permissions]--> RolePermission --[permission_id]--> Permission

Runtime Enforcement:
  Every secured REST endpoint:
    current_user = Depends(require_permission("CODE"))
    -> get_current_user() validates JWT
    -> has_permission(db, user.id, "CODE") does 1+N DB queries

  UI routes mostly use:
    current_user = Depends(get_current_user_ui)
    [permission check done in-function or not at all for some UI routes]
```

---

## 12. Modules Completed vs To Be Implemented

### Completed Modules

| Module | REST API | UI HTML | Notes |
|---|---|---|---|
| Authentication | Yes | Yes | Login, logout, JWT + HttpOnly cookie |
| Dashboard | N/A | Yes | Metrics + recent activity cards |
| Category Master | Yes | Yes | Full CRUD |
| Unit Master | Yes | Yes | Full CRUD |
| Office Master | Yes | Yes | Full CRUD |
| Section Master | Yes | Yes | Full CRUD |
| Financial Year | Yes | Yes | Full CRUD |
| Item Master | Yes | Yes | Full CRUD |
| Opening Stock | Yes | Yes | Full CRUD + AJAX live search table |
| Role Master | Yes | Yes | Full CRUD |
| User Master | Yes | Yes | Full CRUD |
| Permission | Yes | Yes | Full CRUD |
| Role Permission | Yes | Yes | Assignment interface |
| User Role | Yes | Yes | Assignment interface |
| Login History | Yes | Yes | View only |
| Physical Indent | Yes | Yes | Entry + single-step workflow |
| Issue | Yes | Yes | Create, review, post, outward pass UI |
| Receipt | Yes | No | REST API only |
| Stock Return | Yes | No | REST API only |
| Stock Transfer | Yes | No | REST API only |
| Outward Pass | Yes | Partial | Via Issue UI only; no standalone UI |
| Asset Register | Yes | No | REST API only |
| Unserviceable Register | Yes | Partial | View-only UI; no create/update UI |
| Stock Balance Report | Yes | No | REST API only |
| Stock Ledger | Yes | No | REST API only |
| Distribution Register | Yes | No | REST API only |
| Asset Register Report | Yes | No | REST API only |
| Item Transaction Register | Yes | No | REST API only |

### Not Yet Implemented

| Feature | Priority | Description |
|---|---|---|
| Receipt UI | High | HTML pages for creating and posting Goods Receipts from suppliers |
| Stock Return UI | High | HTML pages for recording and posting returns from offices |
| Stock Transfer UI | High | HTML pages for inter-office stock transfer creation and posting |
| Asset Management UI | High | Full HTML asset register: create, view, update, movement history |
| Unserviceable Create UI | High | Form to record new unserviceable material entries |
| Unserviceable Status Update UI | Medium | UI to advance status: repair, condemn, dispose |
| Stock Reports UI | Medium | HTML dashboards for Balance, Ledger, Distribution, all registers |
| Indent Approval Workflow | Medium | OFFICE_APPROVED, HEAD_OFFICE_APPROVED, SENT_TO_STORE, REJECTED states implemented |
| Online Indent Workflow | Low | RequestSource.ONLINE path: office submits online, store receives |
| Supplier Master | Low | Full supplier management with contacts and purchase orders |
| Print / PDF Export | Medium | Print functionality for Indents, Issues, Receipts, Transfer documents |
| E-Waste / Computer UI | Low | Asset sub-register filtered HTML views |
| DB-level Pagination for Opening Stock | Medium | Replace Python-side memory pagination |
| Financial Year Closing | Medium | Year-end close and carry-forward to next FY |
| Stock Adjustment | Medium | STOCK_ADJUST permission defined; no adjustment transaction |
| Asset Condemnation Workflow | Low | Formal condemnation with committee approval |
| Asset Disposal Workflow | Low | Formal disposal tracking |
| Repair Tracking | Low | Send assets for repair, track repair status, receive back |
| Automated Test Suite | High | Unit tests, integration tests for posting and stock calculations |

---

## 13. Identified Flaws and Risks

### CRITICAL Issues

| # | Flaw | File / Function | Impact |
|---|---|---|---|
| C1 | Permission check = N+M DB queries per request | services/permission_service.py has_permission() | Every secured endpoint: 1 role query + N permission queries. No caching. DB overload at scale with many concurrent users. |
| C2 | Auto asset assignment is non-deterministic | routers/ui/indent.py submit_physical_indent_ui() and process_indent_ui() | Assets assigned via .limit(iss_qty) with no ORDER BY. Which specific assets get issued is arbitrary. Creates unreliable audit trail. |
| C3 | Document number race condition | services/document_number_service.py generate_document_number() | SELECT MAX in Python then increment: concurrent requests can both read same value and generate duplicate document numbers. No DB sequence or advisory lock. |
| C4 | JWT token not invalidated on logout | routers/ui/auth.py logout() | Only HttpOnly cookie deleted. The JWT itself stays valid until expiry. Stolen tokens continue working after logout. No blacklist mechanism. |
| C5 | Asset count not verified before issue line creation | routers/ui/indent.py process_indent_ui() | .limit(int(issued_qty)) used without verifying returned count equals issued_qty. Issue lines are created with insufficient assets, only failing later at post_issue() time, leaving data in inconsistent state. |

### MODERATE Issues

| # | Flaw | File / Function | Impact |
|---|---|---|---|
| M1 | Opening stock pagination is fully in-memory | routers/ui/opening_stock.py _filter_and_paginate_opening_stocks() | All opening_stocks loaded into Python list then sliced. Memory spike and slowdown as inventory grows. |
| M2 | issue_no unique constraint is globally scoped, not per-FY | models/issue.py issue_no field | unique=True is table-wide but document_number_service generates per-FY numbers. Conceptual mismatch; could cause confusion if FY handling changes. |
| M3 | Stock calculation opening balance workaround | services/stock_service.py get_item_stock() | Checking for OPENING StockMovement to avoid double-adding OpeningStock is fragile. Historical data imports could create subtle stock miscalculations. |
| M4 | perm_codes cached on user object is never used | dependencies/permissions.py require_permission_ui() | get_current_user_ui() populates user.perm_codes but require_permission_ui() ignores it and re-queries DB. Wasted computation. |
| M5 | Form validation errors discard form state | Multiple UI routers | On failure: redirect with ?error= in query string. User must re-enter all form data. Poor UX. |
| M6 | No CSRF protection | All POST form routes | Cookie auth without CSRF tokens. Vulnerable to cross-site request forgery attacks on any state-changing operation. |
| M7 | Soft delete applied inconsistently | Various models and crud files | Some queries filter is_active=True consistently; others miss it. Soft-deleted records can surface in some list views. |
| M8 | echo=True on production SQLAlchemy engine | core/db.py create_engine() | Every SQL statement logged to stdout. Performance overhead and potential credential/data exposure in logs. |

### MINOR / Design Issues

| # | Flaw | Location | Impact |
|---|---|---|---|
| D1 | Hardcoded year fallback "2026" | document_number_service.py line 20 | When FinancialYear not found, document numbers default to 2026 regardless of actual calendar year. Will generate wrong numbers in future years. |
| D2 | Indent status transitions not enforced | models/enums.py IndentStatus, routers/indent.py | Status machine states defined (DRAFT->SUBMITTED->APPROVED->CLOSED) but no transition validation. Any status can be set directly. |
| D3 | No automated tests | tests/ directory | Directory exists but empty. Zero test coverage for posting service, stock calculations, authentication. High regression risk. |
| D4 | Root requirements.txt is UTF-16 encoded | requirements.txt root file | Causes read failures with standard tools. Only app/requirements.txt is usable. |
| D5 | Supplier model not implemented | Receipt.supplier_name field | Supplier is a plain String field. No supplier master table, purchase orders, or contact management as referenced in architecture docs. |
| D6 | No pagination on several REST GET list endpoints | Multiple router files | Some GET endpoints return unbounded result sets without pagination, will cause timeouts and memory issues at scale. |
| D7 | Cookie lacks Secure flag | routers/ui/auth.py login_submit() | set_cookie(httponly=True, samesite="lax") — secure=True not set. Cookie transmitted in plaintext over HTTP. |
| D8 | Indent receipt page has no print CSS | templates/indents/receipt.html | Receipt is meant to be printed but no print-specific CSS or PDF generation is implemented. |
