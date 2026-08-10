# Central Store Management System / Central Store ERP

## Final Business and Technical Design Reference

**Project scope:** Central Store first, with architecture that can later
support authenticated requests from sections and branch offices.

------------------------------------------------------------------------

# 1. Project Objective

The immediate objective is to build a practical Central Store Management
System for the Central Store and its storekeeper.

The system must record the complete movement of stock into and out of
the Central Store using document-based transactions.

The application should be extensible for future use by sections and
branch offices, but we will NOT overbuild a full department-wide ERP
before the Central Store workflow is working.

Core principle:

> The Central Store transaction system is the source of truth for stock
> movement.

------------------------------------------------------------------------

# 2. Current Technology Stack

-   FastAPI
-   SQLAlchemy 2.x using `Mapped` / `mapped_column`
-   PostgreSQL
-   Pydantic V2
-   Alembic
-   Jinja2
-   Bootstrap
-   Separate API routers and UI routers
-   `app/core`, `app/models`, `app/schemas`, `app/crud`, `app/routers`,
    `app/templates`, `app/static`, `app/services`
-   `app/core/pagination.py`
-   `app/schemas/common.py` with generic `PaginatedResponse[T]`

Development is done on both the home and office computers.

Git is the synchronization mechanism: - develop and test - commit -
push - pull on the other computer - run required migrations/seeds there

Git synchronizes source code, NOT PostgreSQL data.

------------------------------------------------------------------------

# 3. Existing Masters --- DO NOT REDESIGN

The following masters already exist and should remain the foundation.

## 3.1 Category

Category identifies the broad classification of an item.

Examples: - Stationery - IT Equipment - Printing Machinery - Binding
Machinery - E-waste - Scrap

Important existing design:

`Category.type` distinguishes: - `MATERIAL` - `ASSET`

This distinction should be reused instead of introducing another
unnecessary tracking-type field into Item.

------------------------------------------------------------------------

## 3.2 Unit

Examples: - Nos - Ream - Kg - Box - Set

Unit is associated with Item.

------------------------------------------------------------------------

## 3.3 Office

Represents the office/store/organizational destination.

Examples can include: - Central Press - Directorate - Branch offices -
Other offices

The existing design supports future multi-office operation.

------------------------------------------------------------------------

## 3.4 Section

A Section belongs to an Office.

This allows a request or issue to identify: - requesting office -
requesting section

The Central Store is the immediate operational focus.

------------------------------------------------------------------------

## 3.5 Financial Year

Financial Year is used throughout the transaction system.

It will be associated with: - Opening Stock - Indents - Goods Receipts -
Issues - Returns - Transfers - Adjustments - Distribution Register -
Document numbering - Reports

Historical financial years must remain available.

We must NOT delete old-year transactions when a new financial year
begins.

------------------------------------------------------------------------

## 3.6 Item

Item identifies what the store holds.

Examples:

Material: - A4 Paper - Pen - File - Binding Tape

Asset: - Desktop Computer - Printer - UPS - Offset Printing Machine -
Digital Printing Machine - Binding Machine - Cutting Machine - Folding
Machine - Laminating Machine

The Item identifies the type of thing.

The actual physical asset is represented separately in the Asset
Register.

------------------------------------------------------------------------

## 3.7 Opening Stock

Opening Stock establishes the stock position at the beginning of a
financial year.

Conceptually:

Financial Year + Office + Item + Quantity

Opening Stock is the starting point.

Subsequent stock changes must come from posted transactions.

------------------------------------------------------------------------

# 4. Authentication and Authorization --- Already Built

Authentication foundation is already implemented.

Flow:

Login → authenticate user → verify password → get user roles → get role
permissions → generate JWT → record login history → dashboard

Current security components include:

-   `app/core/security.py`
-   `app/services/auth_service.py`
-   `app/services/permission_service.py`
-   `app/dependencies/permissions.py`
-   authentication router
-   login history

JWT design: - short-lived access token - roles/permissions are NOT
stored inside JWT - current roles and permissions are loaded from the
database - permission changes therefore take effect immediately

------------------------------------------------------------------------

# 5. Authentication Database Relationships

## Role → RolePermission → Permission

RolePermission is the many-to-many junction.

## User → UserRole → Role

UserRole is the many-to-many junction.

## User → LoginHistory

LoginHistory is an audit table.

Login History: - read-only from UI - administrators should not
edit/delete it

Unique constraints prevent duplicate assignments.

------------------------------------------------------------------------

# 6. Permission Design

Permission contains:

-   code
-   module
-   action
-   name
-   description
-   common fields such as id, is_active, created_at, updated_at

The user enters: - Module - Action - Description

The system generates: - code - name

Example:

Module = Item Action = Create

Generated:

`ITEM_CREATE`

`Create Item`

The current permission catalogue contains 45 permissions.

ADMIN currently has all 45 permissions.

Permission seed/setup is kept in the repository so authorization data
can be reproduced on another database.

Do NOT run permission seed code automatically on every application
startup.

------------------------------------------------------------------------

# 7. Application Entry and UI Direction

Application startup should be:

Login → Authentication → Dashboard

When an unauthenticated user opens `/`, the application should direct
them to Login.

After successful authentication:

`/dashboard`

The Dashboard is the central workspace.

The sidebar should be logically grouped rather than showing every master
as a flat menu.

Suggested structure:

Dashboard

Masters - Category - Unit - Office - Section - Financial Year - Item

Stock Setup - Opening Stock

Asset Management - Asset Register

Transactions - Indent / Request - Goods Receipt - Issue - Return -
Transfer - Adjustment - Outward Pass

Registers - Item Stock Register - Distribution Register - Transaction
Register - Asset Register - Computer Register - E-Waste Register

Reports - Current Stock - Stock Ledger - Transaction Reports

Administration - Users - Roles - Permissions - Assign Roles - Assign
Permissions - Login History

The actual sidebar should eventually be permission-aware.

Hiding a menu item is only a UI convenience. Backend authorization
remains mandatory.

------------------------------------------------------------------------

# 8. Final Business Scope

The immediate operational scope is:

> Central Store only.

The system must record transactions from and to the Central Store.

Future scope:

> Sections and branch offices can later originate authenticated online
> requests.

The transaction core should NOT be redesigned when online requests are
added.

Version 1:

Physical indent/letter → Storekeeper enters request

Future version:

Section/Branch User → Login → Online Indent → Central Store

Both should use the same Indent document model.

------------------------------------------------------------------------

# 9. Core Business Workflow

The Central Store workflow is:

Section / Branch → Indent / Letter → Central Store → Storekeeper Review
→ Check Availability → Decide Issue Quantity → Issue → Update Stock
Ledger → Update Distribution Register → Generate Outward Pass if
required → Preserve original request/reference

The central transaction relationship is:

Indent → Issue → Stock Movement → Registers/Reports

------------------------------------------------------------------------

# 10. Indent / Request --- FIRST TRANSACTION DOCUMENT

The Indent/Request is the starting document.

It can originate from: - Section - Branch Office

Initially it may be: - physical indent - official letter - other
received request

The storekeeper records it in the application.

## Indent Header

Planned fields:

-   id
-   indent_no
-   indent_date
-   received_date
-   financial_year_id
-   office_id
-   section_id
-   request_type
-   reference_no
-   status
-   remarks
-   created_by
-   created_at
-   updated_at

Request source may later distinguish: - PHYSICAL - ONLINE

This does not need to be implemented immediately if not required.

------------------------------------------------------------------------

# 11. Indent Lines

One Indent can contain many items.

Structure:

Indent - Item A - Item B - Item C - Item D

Each line should contain at least:

-   item_id
-   requested_quantity
-   issued_quantity
-   remarks

Important rule:

`requested_quantity` and `issued_quantity` are separate.

Example:

A4 Paper: - Requested = 20 - Issued = 15

This preserves the actual request and the storekeeper's decision.

------------------------------------------------------------------------

# 12. Storekeeper Availability Decision

The storekeeper checks availability for each requested item.

Example:

A4 Paper: - Requested = 20 - Available = 15 - Issued = 15 - Balance = 0

Pen: - Requested = 100 - Available = 500 - Issued = 100 - Balance = 400

The system must preserve: - requested quantity - available stock at
processing time - actual issued quantity

The final detailed stock logic will be implemented in the
transaction/posting layer.

------------------------------------------------------------------------

# 13. Issue Document

The Indent is the request.

The Issue is the actual stock movement.

Relationship:

Indent → Storekeeper processes → Issue

The Issue must reference the original Indent.

Planned Issue Header:

-   id
-   issue_no
-   issue_date
-   financial_year_id
-   indent_id
-   office_id / destination office
-   section_id / destination section
-   remarks
-   issued_by
-   status
-   created_at
-   posted_at
-   posted_by

Issue Lines:

-   item_id
-   quantity
-   asset_id when applicable
-   remarks

For a material:

Item = A4 Paper Quantity = 20 Asset = NULL

For an asset:

Item = Desktop Computer Quantity = 1 Asset = COMP-0023

------------------------------------------------------------------------

# 14. Posting Rule

Saving a document must NOT automatically change stock.

Initial workflow:

DRAFT → POSTED

Only POSTED documents affect stock.

Later, if the real business process requires approvals:

DRAFT → SUBMITTED → APPROVED → POSTED

Do not build a complicated approval workflow until the Central Store
actually requires it.

------------------------------------------------------------------------

# 15. Stock Ledger / Stock Register

The storekeeper currently maintains a stock register for each item.

The application should represent this as a single Stock Ledger system,
not separate database tables for each item.

UI:

Stock Register → Select Item → Display that item's complete transaction
history

Example:

Date \| Document \| Receipt \| Issue \| Balance 01-Apr \| Opening \| 100
\| \| 100 05-Apr \| GRN-001 \| 50 \| \| 150 10-Apr \| ISS-001 \| \| 20
\| 130 15-Apr \| ISS-002 \| \| 10 \| 120

The ledger must answer:

> Why did the stock change?

Every stock movement must be traceable to its source document.

------------------------------------------------------------------------

# 16. Stock Calculation

Conceptually:

Current Stock = Opening Stock + Receipts + Returns + Transfer Receipts -
Issues - Transfer Issues ± Adjustments

The authoritative history should come from posted stock movements.

Do not directly edit current stock as a substitute for transactions.

------------------------------------------------------------------------

# 17. Distribution Register

The Distribution Register is required per financial year.

It should be a register/report generated from posted Issue documents.

Do NOT duplicate issue data into an independent transaction table.

Example:

Date \| Issue No \| Indent No \| Office \| Section \| Item \| Quantity

The Issue document remains the source of truth.

The Distribution Register is a business view of those posted issues.

------------------------------------------------------------------------

# 18. Outward Pass

The storekeeper issues a pass when an item leaves the premises and the
business rules require an outward pass.

Relationship:

Issue → Out of premises? → YES → Outward Pass

The Pass should reference the Issue.

Do NOT manually re-enter all item details into the Pass.

The Pass should derive its item details from the Issue.

Planned Pass information:

-   pass_no
-   date
-   issue_id
-   indent_id through issue
-   destination
-   authorized_by
-   issued_by
-   status
-   remarks

------------------------------------------------------------------------

# 19. Goods Receipt

Goods Receipt records stock entering the Central Store.

Conceptually:

Source/Supplier → Goods Receipt → Stock IN

Supplier is optional and does not require a permanent Supplier Master at
this stage.

A receipt can reference: - purchase document - invoice - transfer -
other legitimate source

Detailed fields will be finalized when the receipt module is designed.

------------------------------------------------------------------------

# 20. Stock Return

A return brings stock back into the Central Store.

Example:

Section/Office → Return → Stock IN

A return should reference the original Issue where appropriate.

This preserves traceability.

------------------------------------------------------------------------

# 21. Stock Transfer

Future multi-office support:

Store A → Transfer → Store B

Stock effect:

Source Store: OUT Destination Store: IN

The current Central Store focus remains primary, but the existing Office
master allows this future extension.

------------------------------------------------------------------------

# 22. Stock Adjustment

Adjustment is for controlled exceptional situations:

-   shortage
-   excess
-   damaged stock
-   missing stock
-   correction

Adjustments must be controlled and audited.

They should not become a normal substitute for proper transactions.

------------------------------------------------------------------------

# 23. Asset Register --- NEW REQUIRED MODULE

The current masters are sufficient to identify asset-type Items, but
they are NOT sufficient to identify each physical asset.

Therefore we need one separate Asset entity.

Do NOT create separate database tables for: - Computer Register -
Printer Register - Printing Machine Register - Binding Machine Register

Use one Asset Register.

------------------------------------------------------------------------

# 24. Asset Register Scope

The Asset Register must include:

IT equipment: - Desktop computers - Laptops - Printers - Scanners - UPS

Printing machinery: - Offset printing machines - Digital printing
machines - Other printing machinery

Binding machinery: - Perfect binders - Stitching machines - Other
binding equipment

Finishing machinery: - Cutting machines - Folding machines - Laminating
machines

Other individually identifiable durable equipment.

A large printing or binding machine is an Asset just like a computer.

------------------------------------------------------------------------

# 25. Item vs Asset

Item answers:

> What is this?

Asset answers:

> Which physical unit is this?

Example:

Item: Desktop Computer

Assets: - COMP-0001 - COMP-0002 - COMP-0003

Another example:

Item: Offset Printing Machine

Assets: - PM-0001 - PM-0002

All may have the same Item but are physically different assets.

------------------------------------------------------------------------

# 26. Asset Register Planned Fields

Common Asset fields:

-   id
-   asset_no
-   item_id
-   serial_no
-   make
-   model
-   purchase_date
-   purchase_reference
-   office_id
-   section_id
-   status
-   remarks
-   created_at
-   updated_at
-   is_active

Do NOT add every possible machine-specific field to the common Asset
table.

Specialized details can be added later only if the real requirement
justifies them.

------------------------------------------------------------------------

# 27. Asset Status

Possible initial statuses:

-   IN_STORE
-   ISSUED
-   UNDER_REPAIR
-   DAMAGED
-   CONDEMNED
-   E_WASTE
-   DISPOSED

Exact statuses can be refined according to the department's actual
procedure.

------------------------------------------------------------------------

# 28. Asset Transactions

For a material:

Item = A4 Paper Quantity = 20

For an asset:

Item = Desktop Computer Quantity = 1 Asset = COMP-0023

For machinery:

Item = Offset Printing Machine Quantity = 1 Asset = PM-0001

This allows the same Issue system to handle: - consumables - computers -
printers - large printing machines - binding machines - other assets

------------------------------------------------------------------------

# 29. Computer Register

Computer Register should be a filtered view of Asset Register.

Conceptually:

Asset Register → Category/Item filtering → Computer-related assets

There should NOT be a completely separate Computer database.

------------------------------------------------------------------------

# 30. E-Waste Register

E-Waste Register should eventually originate from the Asset/Item
lifecycle.

Example:

Asset → Damaged/obsolete → Condemned → E-Waste → E-Waste Register →
Disposal process

This should be developed later.

------------------------------------------------------------------------

# 31. Transaction Register

Transaction Register should show document-level transaction history.

It should not become a second independent stock system.

Source documents include: - Goods Receipt - Issue - Return - Transfer -
Adjustment

------------------------------------------------------------------------

# 32. Traceability Requirement

A major requirement is document traceability.

If somebody asks:

> Why was 15 reams of A4 paper issued to Section X?

The system should be able to trace:

Stock Ledger → Issue ISS-xxxx → Indent IND-xxxx → Section X → Original
request/reference

Similarly:

Asset → Issue → Indent → destination → Outward Pass, if applicable

This is one of the core purposes of the system.

------------------------------------------------------------------------

# 33. Physical Documents vs Digital Records

Currently the storekeeper receives: - physical indent - official
letter - request

The system should record the document details and preserve the
reference.

The original physical request continues to be retained by the
storekeeper according to the office procedure.

Later, attachment/upload functionality can be added if required.

Do not make document upload a dependency for the first transaction
version.

------------------------------------------------------------------------

# 34. Future Online Request Flow

Current:

Physical Indent/Letter → Storekeeper enters Indent → Storekeeper
processes Issue

Future:

Section/Branch User → Login → Create Online Indent → Submit → Central
Store receives request → Storekeeper processes → Issue → Stock movement

The same Indent core should support both origins.

------------------------------------------------------------------------

# 35. Final Application Architecture

CENTRAL STORE ERP

├── Dashboard │ ├── Masters │ ├── Category │ ├── Unit │ ├── Office │ ├──
Section │ ├── Financial Year │ └── Item │ ├── Stock Setup │ └── Opening
Stock │ ├── Asset Management │ └── Asset Register │ ├── Transactions │
├── Indent / Request │ ├── Goods Receipt │ ├── Issue │ ├── Return │ ├──
Transfer │ ├── Adjustment │ └── Outward Pass │ ├── Registers │ ├── Item
Stock Register │ ├── Distribution Register │ ├── Transaction Register │
├── Asset Register │ ├── Computer Register │ └── E-Waste Register │ ├──
Reports │ ├── Current Stock │ ├── Stock Ledger │ └── Transaction Reports
│ └── Administration ├── Users ├── Roles ├── Permissions ├── Assign
Roles ├── Assign Permissions └── Login History

------------------------------------------------------------------------

# 36. Development Order --- FINAL

We should now stop expanding master CRUDs and build the business
workflow.

## Phase 1 --- Asset Register

1.  Asset model
2.  Asset schema
3.  Asset CRUD
4.  Asset API router
5.  Alembic migration
6.  Asset UI
7.  Test Asset Register

## Phase 2 --- Indent / Request

8.  Indent model
9.  Indent line model
10. Schemas
11. CRUD
12. API
13. UI
14. Storekeeper processing/status

## Phase 3 --- Issue

15. Issue model
16. Issue line model
17. Link Issue to Indent
18. Support material quantity
19. Support asset-level issue
20. Posting logic
21. UI

## Phase 4 --- Stock Ledger

22. Stock movement model
23. Posting service
24. Item-wise stock register
25. Current stock calculation
26. Transaction traceability

## Phase 5 --- Distribution Register

27. Financial-year-wise distribution view/report

## Phase 6 --- Outward Pass

28. Pass model
29. Pass generation from Issue
30. Pass UI/print format

## Phase 7 --- Goods Receipt

31. Receipt document
32. Receipt lines
33. Stock IN posting

## Phase 8 --- Return

34. Return document
35. Stock IN posting

## Phase 9 --- Transfer

36. Transfer document
37. Source OUT
38. Destination IN

## Phase 10 --- Adjustment

39. Controlled stock adjustment
40. Audit trail

## Phase 11 --- Special Registers

41. Asset Register improvements
42. Computer Register view
43. E-Waste Register
44. Other special registers as required

## Phase 12 --- Future Online Requests

45. Section/Branch authentication
46. Online Indent creation
47. Submission workflow
48. Central Store processing queue

------------------------------------------------------------------------

# 37. Important Design Rules

1.  Do not redesign working masters without a real technical/business
    reason.

2.  Do not create separate tables for Computer, Printer, Printing
    Machine, and Binding Machine. Use Item + Asset.

3.  Do not duplicate transaction information into multiple
    source-of-truth tables.

4.  Posted documents are what change stock.

5.  Every stock movement must have a source document.

6.  Requested quantity and issued quantity are separate.

7.  Asset-tracked items identify a specific Asset; material items use
    quantity.

8.  Distribution Register is derived from Issue transactions.

9.  Item Stock Register is derived from Stock Ledger.

10. Computer Register is a filtered Asset Register.

11. E-Waste should eventually originate from the asset/item lifecycle.

12. Historical financial-year data must remain available.

13. Authentication and backend authorization remain mandatory even when
    UI menus/buttons are hidden.

14. Do not build the entire department-wide workflow before the Central
    Store workflow is usable.

15. Keep the transaction architecture extensible for future
    section/branch online requests.

16. Git synchronizes code; PostgreSQL data must be reproduced using
    migrations/seed/setup processes where required.

------------------------------------------------------------------------

# 38. First Real Business Workflow to Complete

The first complete vertical slice should be:

Physical Indent / Letter → Indent Entry → Multiple Indent Lines →
Storekeeper Checks Availability → Issue Quantity Entered → Issue
Document → Post Issue → Stock Ledger Updated → Distribution Register
Updated → Outward Pass when required → Original Indent remains traceable

Once this works, the Central Store will have its first genuinely useful
end-to-end digital workflow.

------------------------------------------------------------------------

# 39. Immediate Next Development Task

Do NOT start transactions yet.

First build:

## Asset Register

Reason:

Issue transactions must be capable of handling individually tracked
assets such as: - computers - printers - offset printing machines -
digital printing machines - binding machines - cutting machines - other
durable equipment

The Asset Register is therefore a dependency of the Issue design.

The first implementation should use the current project conventions and
inspect the existing Item/Category models before writing code.

The next technical sequence is:

Asset Model → Schema → CRUD → API Router → Alembic Migration → UI → Test
→ Git Commit/Push → Office Pull/Verify → Indent

------------------------------------------------------------------------

# 40. Final Conceptual Model

The entire Central Store system can be understood as:

MASTER DATA ↓ ITEM ↓ ┌─────────────────────────────┐ │ │ MATERIAL ASSET
│ │ Quantity Stock Individual Asset │ │ └──────────────┬──────────────┘
↓ TRANSACTIONS ↓ ┌────────┼────────┐ ↓ ↓ ↓ Receipt Issue Return │ ↓
STOCK MOVEMENT │ ┌──────┴──────┐ ↓ ↓ Stock Ledger Distribution │ ↓
Reports

For an Issue:

INDENT ↓ ISSUE ↓ STOCK MOVEMENT ↓ DISTRIBUTION REGISTER ↓ OUTWARD PASS
(if required)

For an asset:

INDENT ↓ ISSUE ↓ ASSET MOVEMENT ↓ ASSET REGISTER ↓ COMPUTER / MACHINERY
/ OTHER ASSET VIEW

This is the design baseline for the Central Store Management System.
