from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.asset_movement import AssetMovement
from app.models.enums import (
    AssetMovementType,
    AssetStatus,
    Category_Type,
    FulfillmentType,
    IndentStatus,
    MovementType,
    TransactionStatus,
)
from app.models.indent import Indent
from app.models.issue import Issue
from app.models.petty_purchase import PettyPurchase
from app.models.receipt import Receipt, ReceiptLineAsset
from app.models.stock_movement import StockMovement
from app.models.stock_return import StockReturn
from app.models.stock_transfer import StockTransfer
from app.services.scope_service import get_stock_office_id
from app.services.stock_service import get_item_stock, validate_stock_availability
from app.crud.asset import generate_asset_number
from app.models.asset_detail import AssetDetail


def _is_asset_item(item) -> bool:
    return bool(item and item.category and item.category.type == Category_Type.ASSET)


def _is_petty_purchase_line(line) -> bool:
    return getattr(line, "fulfillment_type", None) == FulfillmentType.PETTY_PURCHASE


def _require_whole_asset_quantity(quantity: float, item_name: str) -> int:
    qty = float(quantity)
    if not qty.is_integer():
        raise ValueError(
            f"Asset item '{item_name}' must have a whole-number quantity."
        )
    count = int(qty)
    if count <= 0:
        raise ValueError(f"Asset item '{item_name}' must have a quantity greater than zero.")
    return count


def _get_active_line_assets(line):
    return [
        line_asset.asset
        for line_asset in line.assets
        if line_asset.asset and line_asset.asset.is_active
    ]


def post_issue(
    db: Session,
    issue_id: int,
    user_id: Optional[int] = None,
) -> Issue:
    """
    Atomically post an Issue document.

    MATERIAL line:
        validate material stock and create one StockMovement(ISSUE).

    ASSET line:
        validate the exact physical assets selected for the line and create
        AssetMovement(ISSUE) records. No quantity StockMovement is created.

    PETTY_PURCHASE is intentionally reserved for the petty-purchase workflow.
    Until that workflow is posted, such lines are rejected rather than being
    incorrectly treated as warehouse stock issues.
    """
    issue = (
        db.query(Issue)
        .filter(Issue.id == issue_id, Issue.is_active == True)
        .first()
    )
    if not issue:
        raise ValueError("Issue document not found.")

    if issue.status == TransactionStatus.POSTED:
        raise ValueError("Issue is already posted.")
    if issue.status == TransactionStatus.CANCELLED:
        raise ValueError("Cannot post a cancelled issue.")

    indent = (
        db.query(Indent)
        .filter(Indent.id == issue.indent_id, Indent.is_active == True)
        .first()
    )
    if not indent:
        raise ValueError("Linked Indent not found.")
    if indent.status == IndentStatus.CLOSED:
        raise ValueError("Linked Indent is already closed.")
    if issue.financial_year_id != indent.financial_year_id:
        raise ValueError("Issue financial year must match the linked Indent financial year.")
    if issue.office_id != indent.office_id:
        raise ValueError("Issue destination office must match the linked Indent office.")
    if issue.section_id != indent.section_id:
        raise ValueError("Issue destination section must match the linked Indent section.")
    if not issue.lines:
        raise ValueError("Issue document contains no line items.")

    store_office_id = get_stock_office_id(db, indent.office_id)
    selected_asset_ids: set[int] = set()

    # -------------------------
    # Pre-validation
    # -------------------------
    for line in issue.lines:
        item = line.item
        if not item:
            raise ValueError(f"Item for line ID {line.id} not found.")

        indent_line = next(
            (il for il in indent.lines if il.item_id == line.item_id and il.is_active),
            None,
        )
        if not indent_line:
            raise ValueError(f"Item '{item.name}' is not present in the linked Indent.")

        if _is_petty_purchase_line(indent_line):
            if _is_asset_item(item):
                raise ValueError(
                    f"Asset item '{item.name}' cannot currently be fulfilled through Petty Purchase."
                )
            purchase = (
                db.query(PettyPurchase)
                .filter(
                    PettyPurchase.indent_line_id == indent_line.id,
                    PettyPurchase.is_active == True,
                    PettyPurchase.status == TransactionStatus.DRAFT,
                )
                .first()
            )
            if not purchase:
                raise ValueError(
                    f"Petty Purchase record is missing for Indent line '{item.name}'."
                )
            if abs(float(purchase.quantity) - float(line.quantity)) > 0.000001:
                raise ValueError(
                    f"Petty Purchase quantity ({purchase.quantity}) must match Issue quantity "
                    f"({line.quantity}) for '{item.name}'."
                )

        if _is_asset_item(item):
            expected_count = _require_whole_asset_quantity(line.quantity, item.name)
            line_assets = _get_active_line_assets(line)

            if len(line_assets) != expected_count:
                raise ValueError(
                    f"Selected assets count ({len(line_assets)}) must match issue quantity "
                    f"({expected_count}) for item '{item.name}'."
                )

            for asset in line_assets:
                if asset.id in selected_asset_ids:
                    raise ValueError(f"Asset '{asset.asset_no}' selected multiple times.")
                selected_asset_ids.add(asset.id)

                if asset.item_id != line.item_id:
                    raise ValueError(
                        f"Asset '{asset.asset_no}' does not match line item '{item.name}'."
                    )
                if asset.status != AssetStatus.IN_STORE:
                    raise ValueError(
                        f"Asset '{asset.asset_no}' is not IN_STORE "
                        f"(Current status: {asset.status})."
                    )
                if asset.office_id != store_office_id:
                    raise ValueError(
                        f"Asset '{asset.asset_no}' is not currently in the source store."
                    )
        elif not _is_petty_purchase_line(indent_line):
            validate_stock_availability(
                db=db,
                item_id=line.item_id,
                office_id=store_office_id,
                required_qty=float(line.quantity),
                financial_year_id=issue.financial_year_id,
            )

    try:
        # -------------------------
        # Atomic posting execution
        # -------------------------
        indent_lines = {il.item_id: il for il in indent.lines if il.is_active}

        for line in issue.lines:
            item = line.item
            indent_line = indent_lines.get(line.item_id)
            if not indent_line:
                raise ValueError(
                    f"Item ID {line.item_id} is not present in the linked Indent."
                )

            if _is_asset_item(item):
                # Asset issue: ONLY AssetMovement + current asset snapshot update.
                for line_asset in line.assets:
                    asset = line_asset.asset
                    if not asset or not asset.is_active:
                        raise ValueError("One or more selected assets are no longer active.")

                    from_office_id = asset.office_id
                    from_section_id = asset.section_id

                    asset.status = AssetStatus.ISSUED
                    asset.office_id = issue.office_id
                    asset.section_id = issue.section_id

                    db.add(
                        AssetMovement(
                            asset_id=asset.id,
                            movement_type=AssetMovementType.ISSUE,
                            from_office_id=from_office_id,
                            from_section_id=from_section_id,
                            to_office_id=issue.office_id,
                            to_section_id=issue.section_id,
                            reference_document=issue.issue_no,
                            movement_date=func.now(),
                            remarks=f"Issued via Issue #{issue.issue_no}",
                        )
                    )
            elif _is_petty_purchase_line(indent_line):
                # Direct local/petty purchase: item goes from vendor to requester.
                # It never becomes Central Store stock. The purchase record and
                # Issue provide the audit trail.
                purchase = db.query(PettyPurchase).filter(
                    PettyPurchase.indent_line_id == indent_line.id,
                    PettyPurchase.is_active == True,
                ).first()
                if not purchase:
                    raise ValueError(
                        f"Petty Purchase record is missing for Indent line '{item.name}'."
                    )
                purchase.status = TransactionStatus.POSTED
                purchase.posted_at = func.now()
            else:
                # Material issue: quantity stock movement only.
                db.add(
                    StockMovement(
                        financial_year_id=issue.financial_year_id,
                        item_id=line.item_id,
                        office_id=store_office_id,
                        # Section is retained only as transaction context,
                        # not as a stock-ownership dimension.
                        section_id=issue.section_id,
                        movement_type=MovementType.ISSUE,
                        quantity_in=0.0,
                        quantity_out=line.quantity,
                        movement_date=func.now(),
                        reference_type="ISSUE",
                        reference_id=issue.id,
                        reference_no=issue.issue_no,
                        remarks=line.remarks or f"Issue #{issue.issue_no}",
                    )
                )

            indent_line.issued_quantity = line.quantity

        indent.status = IndentStatus.CLOSED
        indent.closed_by_id = user_id
        indent.closed_at = func.now()

        issue.status = TransactionStatus.POSTED
        issue.posted_by_id = user_id
        issue.posted_at = func.now()

        db.commit()
        db.refresh(issue)
        return issue
    except Exception:
        db.rollback()
        raise


def post_receipt(
    db: Session,
    receipt_id: int,
    user_id: Optional[int] = None,
) -> Receipt:
    """
    Post a Goods Receipt.

    MATERIAL lines create StockMovement(RECEIPT).
    ASSET lines create one physical Asset per received unit plus an
    AssetMovement(RECEIPT). No quantity StockMovement is created for assets.
    """
    receipt = (
        db.query(Receipt)
        .filter(Receipt.id == receipt_id, Receipt.is_active == True)
        .first()
    )
    if not receipt:
        raise ValueError("Receipt document not found.")
    if receipt.status == TransactionStatus.POSTED:
        raise ValueError("Receipt is already posted.")
    if receipt.status == TransactionStatus.CANCELLED:
        raise ValueError("Cannot post a cancelled receipt.")
    if not receipt.lines:
        raise ValueError("Receipt document contains no line items.")

    try:
        for line in receipt.lines:
            item = line.item
            if not item:
                raise ValueError(f"Item for receipt line ID {line.id} not found.")

            if _is_asset_item(item):
                # Asset receipt: each physical unit becomes an Asset.
                qty = float(line.quantity)
                if not qty.is_integer():
                    raise ValueError(
                        f"Asset item '{item.name}' must have a whole-number receipt quantity."
                    )
                expected_count = int(qty)
                entries = [entry for entry in line.asset_entries if entry.is_active]
                if len(entries) != expected_count:
                    raise ValueError(
                        f"Asset item '{item.name}' requires exactly {expected_count} asset detail entries."
                    )

                stock_office_id = get_stock_office_id(db, receipt.office_id)
                seen_serials: set[str] = set()
                seen_asset_nos: set[str] = set()
                for entry in entries:
                    asset_no = entry.asset_no.strip().upper() if entry.asset_no else None
                    if asset_no:
                        if asset_no in seen_asset_nos or db.query(Asset.id).filter(Asset.asset_no == asset_no).first():
                            raise ValueError(f"Asset number '{asset_no}' already exists.")
                        seen_asset_nos.add(asset_no)
                    else:
                        asset_no = generate_asset_number(db, line.item_id)
                        seen_asset_nos.add(asset_no)

                    serial_no = entry.serial_no.strip() if entry.serial_no else None
                    if serial_no:
                        serial_key = serial_no.casefold()
                        if serial_key in seen_serials or db.query(Asset.id).filter(Asset.serial_no == serial_no).first():
                            raise ValueError(f"Serial number '{serial_no}' already exists.")
                        seen_serials.add(serial_key)

                    asset = Asset(
                        asset_no=asset_no,
                        item_id=line.item_id,
                        serial_no=serial_no,
                        office_id=stock_office_id,
                        section_id=None,
                        status=AssetStatus.IN_STORE,
                        remarks=entry.remarks or line.remarks or f"Received via Receipt #{receipt.receipt_no}",
                    )
                    asset.asset_detail = AssetDetail(
                        make=entry.make,
                        model=entry.model,
                        purchase_date=entry.purchase_date or receipt.receipt_date,
                        purchase_reference=entry.purchase_reference or receipt.reference_no,
                        purchase_value=entry.purchase_value if entry.purchase_value is not None else line.unit_price,
                        warranty_expiry_date=entry.warranty_expiry_date,
                        technical_specifications=entry.technical_specifications,
                    )
                    asset.movements.append(
                        AssetMovement(
                            movement_type=AssetMovementType.RECEIPT,
                            to_office_id=stock_office_id,
                            to_section_id=None,
                            reference_document=receipt.receipt_no,
                            movement_date=func.now(),
                            remarks=f"Received via Goods Receipt #{receipt.receipt_no}",
                        )
                    )
                    db.add(asset)
            else:
                db.add(
                    StockMovement(
                        financial_year_id=receipt.financial_year_id,
                        item_id=line.item_id,
                        office_id=get_stock_office_id(db, receipt.office_id),
                        section_id=receipt.section_id,
                        movement_type=MovementType.RECEIPT,
                        quantity_in=line.quantity,
                        quantity_out=0.0,
                        movement_date=func.now(),
                        reference_type="RECEIPT",
                        reference_id=receipt.id,
                        reference_no=receipt.receipt_no,
                        remarks=line.remarks or f"Receipt #{receipt.receipt_no}",
                    )
                )

        receipt.status = TransactionStatus.POSTED
        receipt.posted_by_id = user_id
        receipt.posted_at = func.now()

        db.commit()
        db.refresh(receipt)
        return receipt
    except Exception:
        db.rollback()
        raise


def post_return(
    db: Session,
    return_id: int,
    user_id: Optional[int] = None,
) -> StockReturn:
    """
    Post a Return.

    MATERIAL -> StockMovement RETURN IN.
    ASSET -> AssetMovement RETURN and asset snapshot moved to the receiving
             store. No quantity StockMovement is created for assets.
    """
    stock_return = (
        db.query(StockReturn)
        .filter(StockReturn.id == return_id, StockReturn.is_active == True)
        .first()
    )
    if not stock_return:
        raise ValueError("Return document not found.")
    if stock_return.status == TransactionStatus.POSTED:
        raise ValueError("Return is already posted.")
    if stock_return.status == TransactionStatus.CANCELLED:
        raise ValueError("Cannot post a cancelled return.")
    if not stock_return.lines:
        raise ValueError("Return document contains no line items.")

    receiving_store_office_id = get_stock_office_id(db, stock_return.office_id)
    selected_asset_ids: set[int] = set()

    # Pre-validation
    for line in stock_return.lines:
        item = line.item
        if not item:
            raise ValueError(f"Item for return line ID {line.id} not found.")

        if _is_asset_item(item):
            expected_count = _require_whole_asset_quantity(line.quantity, item.name)
            line_assets = _get_active_line_assets(line)
            if len(line_assets) != expected_count:
                raise ValueError(
                    f"Selected assets count ({len(line_assets)}) must match return quantity "
                    f"({expected_count}) for item '{item.name}'."
                )

            for asset in line_assets:
                if asset.id in selected_asset_ids:
                    raise ValueError(f"Asset '{asset.asset_no}' selected multiple times.")
                selected_asset_ids.add(asset.id)
                if asset.item_id != line.item_id:
                    raise ValueError(
                        f"Asset '{asset.asset_no}' does not match line item '{item.name}'."
                    )
                if asset.status == AssetStatus.IN_STORE:
                    raise ValueError(
                        f"Asset '{asset.asset_no}' is already IN_STORE; it cannot be returned as an outward asset."
                    )
        else:
            # This is a material return to the receiving store.
            # No stock availability validation is required for an inbound return.
            continue

    try:
        for line in stock_return.lines:
            item = line.item

            if _is_asset_item(item):
                for line_asset in line.assets:
                    asset = line_asset.asset
                    if not asset or not asset.is_active:
                        raise ValueError("One or more selected assets are no longer active.")

                    from_office_id = asset.office_id
                    from_section_id = asset.section_id

                    asset.status = AssetStatus.IN_STORE
                    asset.office_id = receiving_store_office_id
                    asset.section_id = None

                    db.add(
                        AssetMovement(
                            asset_id=asset.id,
                            movement_type=AssetMovementType.RETURN,
                            from_office_id=from_office_id,
                            from_section_id=from_section_id,
                            to_office_id=receiving_store_office_id,
                            to_section_id=None,
                            reference_document=stock_return.return_no,
                            movement_date=func.now(),
                            remarks=f"Returned via Return #{stock_return.return_no}",
                        )
                    )
            else:
                db.add(
                    StockMovement(
                        financial_year_id=stock_return.financial_year_id,
                        item_id=line.item_id,
                        office_id=receiving_store_office_id,
                        section_id=stock_return.section_id,
                        movement_type=MovementType.RETURN,
                        quantity_in=line.quantity,
                        quantity_out=0.0,
                        movement_date=func.now(),
                        reference_type="RETURN",
                        reference_id=stock_return.id,
                        reference_no=stock_return.return_no,
                        remarks=line.remarks or f"Return #{stock_return.return_no}",
                    )
                )

        stock_return.status = TransactionStatus.POSTED
        stock_return.posted_by_id = user_id
        stock_return.posted_at = func.now()

        db.commit()
        db.refresh(stock_return)
        return stock_return
    except Exception:
        db.rollback()
        raise


def post_transfer(
    db: Session,
    transfer_id: int,
    user_id: Optional[int] = None,
) -> StockTransfer:
    """
    Post a Stock Transfer.

    MATERIAL -> StockMovement OUT + IN.
    ASSET -> AssetMovement TRANSFER + current asset location update.
             No quantity StockMovement is created for assets.
    """
    transfer = (
        db.query(StockTransfer)
        .filter(StockTransfer.id == transfer_id, StockTransfer.is_active == True)
        .first()
    )
    if not transfer:
        raise ValueError("Transfer document not found.")
    if transfer.status == TransactionStatus.POSTED:
        raise ValueError("Transfer is already posted.")
    if transfer.status == TransactionStatus.CANCELLED:
        raise ValueError("Cannot post a cancelled transfer.")
    if not transfer.lines:
        raise ValueError("Transfer document contains no line items.")

    from_stock_office_id = get_stock_office_id(db, transfer.from_office_id)
    to_stock_office_id = get_stock_office_id(db, transfer.to_office_id)

    if from_stock_office_id == to_stock_office_id:
        raise ValueError("Source and destination stock stores cannot be identical.")

    selected_asset_ids: set[int] = set()

    # Pre-validation
    for line in transfer.lines:
        item = line.item
        if not item:
            raise ValueError(f"Item for transfer line ID {line.id} not found.")

        if _is_asset_item(item):
            expected_count = _require_whole_asset_quantity(line.quantity, item.name)
            line_assets = _get_active_line_assets(line)
            if len(line_assets) != expected_count:
                raise ValueError(
                    f"Selected assets count ({len(line_assets)}) must match transfer quantity "
                    f"({expected_count}) for item '{item.name}'."
                )

            for asset in line_assets:
                if asset.id in selected_asset_ids:
                    raise ValueError(f"Asset '{asset.asset_no}' selected multiple times.")
                selected_asset_ids.add(asset.id)

                if asset.item_id != line.item_id:
                    raise ValueError(
                        f"Asset '{asset.asset_no}' does not match line item '{item.name}'."
                    )
                if asset.office_id != transfer.from_office_id:
                    raise ValueError(
                        f"Asset '{asset.asset_no}' is not currently in the source office."
                    )
                if transfer.from_section_id is not None and asset.section_id != transfer.from_section_id:
                    raise ValueError(
                        f"Asset '{asset.asset_no}' is not currently in the source section."
                    )
                if asset.status == AssetStatus.DISPOSED:
                    raise ValueError(f"Disposed asset '{asset.asset_no}' cannot be transferred.")
        else:
            validate_stock_availability(
                db=db,
                item_id=line.item_id,
                office_id=from_stock_office_id,
                required_qty=float(line.quantity),
                financial_year_id=transfer.financial_year_id,
            )

    try:
        for line in transfer.lines:
            item = line.item

            if _is_asset_item(item):
                for line_asset in line.assets:
                    asset = line_asset.asset
                    if not asset or not asset.is_active:
                        raise ValueError("One or more selected assets are no longer active.")

                    from_office_id = asset.office_id
                    from_section_id = asset.section_id

                    asset.office_id = transfer.to_office_id
                    asset.section_id = transfer.to_section_id

                    # An Asset transferred into another store is physically in-store;
                    # a transfer to a section is considered assigned.
                    asset.status = (
                        AssetStatus.IN_STORE
                        if transfer.to_section_id is None
                        else AssetStatus.ISSUED
                    )

                    db.add(
                        AssetMovement(
                            asset_id=asset.id,
                            movement_type=AssetMovementType.TRANSFER,
                            from_office_id=from_office_id,
                            from_section_id=from_section_id,
                            to_office_id=transfer.to_office_id,
                            to_section_id=transfer.to_section_id,
                            reference_document=transfer.transfer_no,
                            movement_date=func.now(),
                            remarks=f"Transferred via Transfer #{transfer.transfer_no}",
                        )
                    )
            else:
                db.add(
                    StockMovement(
                        financial_year_id=transfer.financial_year_id,
                        item_id=line.item_id,
                        office_id=from_stock_office_id,
                        section_id=transfer.from_section_id,
                        movement_type=MovementType.TRANSFER_OUT,
                        quantity_in=0.0,
                        quantity_out=line.quantity,
                        movement_date=func.now(),
                        reference_type="TRANSFER",
                        reference_id=transfer.id,
                        reference_no=transfer.transfer_no,
                        remarks=f"Transfer OUT #{transfer.transfer_no}",
                    )
                )
                db.add(
                    StockMovement(
                        financial_year_id=transfer.financial_year_id,
                        item_id=line.item_id,
                        office_id=to_stock_office_id,
                        section_id=transfer.to_section_id,
                        movement_type=MovementType.TRANSFER_IN,
                        quantity_in=line.quantity,
                        quantity_out=0.0,
                        movement_date=func.now(),
                        reference_type="TRANSFER",
                        reference_id=transfer.id,
                        reference_no=transfer.transfer_no,
                        remarks=f"Transfer IN #{transfer.transfer_no}",
                    )
                )

        transfer.status = TransactionStatus.POSTED
        transfer.posted_by_id = user_id
        transfer.posted_at = func.now()

        db.commit()
        db.refresh(transfer)
        return transfer
    except Exception:
        db.rollback()
        raise
