from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.enums import Category_Type, TransactionStatus, FulfillmentType
from app.models.category import Category
from app.models.indent import Indent
from app.models.indent_line import IndentLine
from app.models.item import Item
from app.models.petty_purchase import PettyPurchase
from app.schemas.petty_purchase import PettyPurchaseCreate
from app.services.document_number_service import generate_document_number


def create_petty_purchase(
    db: Session,
    indent_id: int,
    indent_line_id: int,
    item_id: int,
    quantity: float,
    purchase: PettyPurchaseCreate,
    user_id: Optional[int] = None,
) -> PettyPurchase:
    indent = db.query(Indent).filter(Indent.id == indent_id, Indent.is_active == True).first()
    if not indent:
        raise ValueError("Indent not found.")
    if indent.status == "CLOSED":
        raise ValueError("Cannot create a petty purchase for a closed Indent.")

    line = db.query(IndentLine).filter(
        IndentLine.id == indent_line_id,
        IndentLine.indent_id == indent_id,
        IndentLine.is_active == True,
    ).first()
    if not line:
        raise ValueError("Indent line not found.")
    if line.item_id != item_id:
        raise ValueError("Petty purchase item does not match the Indent line.")
    if line.fulfillment_type != FulfillmentType.PETTY_PURCHASE:
        raise ValueError("Petty Purchase can only be created for an Indent line marked PETTY_PURCHASE.")

    existing = db.query(PettyPurchase).filter(
        PettyPurchase.indent_line_id == indent_line_id,
        PettyPurchase.status != TransactionStatus.POSTED,
    ).first()
    if existing:
        if quantity <= 0 or quantity > float(line.requested_quantity):
            raise ValueError("Petty purchase quantity must be greater than zero and not exceed the Indent request.")
        # One petty-purchase record belongs to one IndentLine. Reuse and
        # reactivate it when the line moves back to PETTY_PURCHASE.
        existing.is_active = True
        return update_petty_purchase_from_input(db, existing, quantity, purchase)

    item = (
        db.query(Item)
        .join(Category, Item.category_id == Category.id)
        .filter(Item.id == item_id, Item.is_active == True, Category.is_active == True)
        .first()
    )
    if not item:
        raise ValueError("Item not found.")
    if item.category.type != Category_Type.MATERIAL:
        raise ValueError("Petty Purchase is currently supported only for MATERIAL items.")

    if quantity <= 0 or quantity > float(line.requested_quantity):
        raise ValueError("Petty purchase quantity must be greater than zero and not exceed the Indent request.")

    purchase_date = purchase.purchase_date or date.today()
    unit_price = purchase.unit_price
    total_amount = (unit_price * Decimal(str(quantity))) if unit_price is not None else None
    petty_no = generate_document_number(
        db=db,
        model_class=PettyPurchase,
        number_field_name="petty_purchase_no",
        prefix="PP",
        financial_year_id=indent.financial_year_id,
    )

    db_purchase = PettyPurchase(
        petty_purchase_no=petty_no,
        indent_id=indent_id,
        indent_line_id=indent_line_id,
        item_id=item_id,
        quantity=quantity,
        purchase_date=purchase_date,
        supplier_name=purchase.supplier_name.strip() if purchase.supplier_name else None,
        reference_no=purchase.reference_no.strip() if purchase.reference_no else None,
        unit_price=unit_price,
        total_amount=total_amount,
        status=TransactionStatus.DRAFT,
        remarks=purchase.remarks.strip() if purchase.remarks else None,
        created_by_id=user_id,
    )
    db.add(db_purchase)
    return db_purchase


def update_petty_purchase_from_input(
    db: Session,
    record: PettyPurchase,
    quantity: float,
    purchase: PettyPurchaseCreate,
) -> PettyPurchase:
    if record.status == TransactionStatus.POSTED:
        raise ValueError("Cannot modify a posted petty purchase.")
    if quantity <= 0 or quantity > float(record.indent_line.requested_quantity):
        raise ValueError("Petty purchase quantity must be greater than zero and not exceed the Indent request.")
    if purchase.unit_price is not None and purchase.unit_price < 0:
        raise ValueError("Unit price cannot be negative.")

    record.quantity = quantity
    record.purchase_date = purchase.purchase_date or record.purchase_date or date.today()
    record.supplier_name = purchase.supplier_name.strip() if purchase.supplier_name else None
    record.reference_no = purchase.reference_no.strip() if purchase.reference_no else None
    record.unit_price = purchase.unit_price
    record.total_amount = (
        purchase.unit_price * Decimal(str(quantity))
        if purchase.unit_price is not None
        else None
    )
    record.remarks = purchase.remarks.strip() if purchase.remarks else None
    return record


def get_petty_purchase_for_indent_line(
    db: Session,
    indent_line_id: int,
) -> Optional[PettyPurchase]:
    return db.query(PettyPurchase).filter(
        PettyPurchase.indent_line_id == indent_line_id,
        PettyPurchase.is_active == True,
    ).first()


def get_petty_purchase_by_id(db: Session, petty_purchase_id: int) -> Optional[PettyPurchase]:
    return db.query(PettyPurchase).filter(
        PettyPurchase.id == petty_purchase_id,
        PettyPurchase.is_active == True,
    ).first()
