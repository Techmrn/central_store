from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.asset_movement import AssetMovement
from app.models.enums import AssetMovementType, AssetStatus, Category_Type, IndentStatus, MovementType, TransactionStatus
from app.models.indent import Indent
from app.models.issue import Issue
from app.models.receipt import Receipt
from app.models.stock_movement import StockMovement
from app.models.stock_return import StockReturn
from app.models.stock_transfer import StockTransfer
from app.services.scope_service import get_stock_office_id
from app.services.stock_service import get_item_stock, validate_stock_availability


def post_issue(
    db: Session,
    issue_id: int,
    user_id: Optional[int] = None,
) -> Issue:
    """
    Atomically post an Issue document.
    - Check stock availability
    - Create stock movements
    - Create asset movements if asset items
    - Close linked Indent
    - Lock Issue document
    """
    issue = db.query(Issue).filter(Issue.id == issue_id, Issue.is_active == True).first()
    if not issue:
        raise ValueError("Issue document not found.")

    if issue.status == TransactionStatus.POSTED:
        raise ValueError("Issue is already posted.")

    if issue.status == TransactionStatus.CANCELLED:
        raise ValueError("Cannot post a cancelled issue.")

    indent = db.query(Indent).filter(Indent.id == issue.indent_id, Indent.is_active == True).first()
    if not indent:
        raise ValueError("Linked Indent not found.")

    if indent.status == IndentStatus.CLOSED:
        raise ValueError("Linked Indent is already closed.")

    if not issue.lines:
        raise ValueError("Issue document contains no line items.")

    selected_asset_ids = set()

    # Pre-validation phase
    for line in issue.lines:
        item = line.item
        if not item:
            raise ValueError(f"Item for line ID {line.id} not found.")

        # Determine if Asset category
        is_asset_item = (item.category and item.category.type == Category_Type.ASSET)

        if is_asset_item:
            line_assets = [la.asset for la in line.assets if la.asset and la.asset.is_active]
            if len(line_assets) != int(line.quantity):
                raise ValueError(
                    f"Selected assets count ({len(line_assets)}) must match issue quantity ({int(line.quantity)}) for item '{item.name}'."
                )

            for asset in line_assets:
                if asset.id in selected_asset_ids:
                    raise ValueError(f"Asset '{asset.asset_no}' selected multiple times.")
                selected_asset_ids.add(asset.id)

                if asset.status != AssetStatus.IN_STORE:
                    raise ValueError(
                        f"Asset '{asset.asset_no}' is not IN_STORE (Current status: {asset.status})."
                    )
                if asset.item_id != line.item_id:
                    raise ValueError(
                        f"Asset '{asset.asset_no}' does not match line item '{item.name}'."
                    )

        # Stock availability check (Store source office is central store / indent source office)
        store_office_id = get_stock_office_id(db, indent.office_id)
        validate_stock_availability(
            db=db,
            item_id=line.item_id,
            office_id=store_office_id,
            required_qty=line.quantity,
            financial_year_id=issue.financial_year_id,
        )

    try:
        # Atomic Posting Execution Phase
        for line in issue.lines:
            store_office_id = get_stock_office_id(db, indent.office_id)

            # 1. Create Stock Movement (OUT)
            sm = StockMovement(
                financial_year_id=issue.financial_year_id,
                item_id=line.item_id,
                office_id=store_office_id,
                section_id=indent.section_id,
                movement_type=MovementType.ISSUE,
                quantity_in=0.0,
                quantity_out=line.quantity,
                movement_date=func.now(),
                reference_type="ISSUE",
                reference_id=issue.id,
                reference_no=issue.issue_no,
                remarks=line.remarks or f"Issue #{issue.issue_no}",
            )
            db.add(sm)

            # 2. Asset Movements if Asset Item
            for line_asset in line.assets:
                asset = line_asset.asset
                if asset:
                    from_office_id = asset.office_id
                    from_section_id = asset.section_id

                    # Update Asset Status & Location
                    asset.status = AssetStatus.ISSUED
                    asset.office_id = issue.office_id
                    asset.section_id = issue.section_id

                    # Create AssetMovement
                    am = AssetMovement(
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
                    db.add(am)

            # 3. Update IndentLine issued_quantity
            indent_line = next((il for il in indent.lines if il.item_id == line.item_id and il.is_active), None)
            if indent_line:
                indent_line.issued_quantity = line.quantity

        # 4. Close Linked Indent
        indent.status = IndentStatus.CLOSED
        indent.closed_by_id = user_id
        indent.closed_at = func.now()

        # 5. Update Issue Document Status to POSTED
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
    Atomically post a Goods Receipt document.
    - Create stock movements (RECEIPT)
    - Lock Receipt document
    """
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id, Receipt.is_active == True).first()
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
            sm = StockMovement(
                financial_year_id=receipt.financial_year_id,
                item_id=line.item_id,
                office_id=receipt.office_id,
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
            db.add(sm)

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
    Atomically post a Stock Return document.
    - Increase stock in ledger
    - Update Asset status back to IN_STORE and location back to store
    - Lock Return document
    """
    stock_return = db.query(StockReturn).filter(StockReturn.id == return_id, StockReturn.is_active == True).first()
    if not stock_return:
        raise ValueError("Return document not found.")

    if stock_return.status == TransactionStatus.POSTED:
        raise ValueError("Return is already posted.")

    if stock_return.status == TransactionStatus.CANCELLED:
        raise ValueError("Cannot post a cancelled return.")

    if not stock_return.lines:
        raise ValueError("Return document contains no line items.")

    try:
        for line in stock_return.lines:
            # 1. Stock Movement (RETURN -> quantity_in)
            sm = StockMovement(
                financial_year_id=stock_return.financial_year_id,
                item_id=line.item_id,
                office_id=stock_return.office_id,
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
            db.add(sm)

            # 2. Asset Return logic
            for line_asset in line.assets:
                asset = line_asset.asset
                if asset:
                    from_office_id = asset.office_id
                    from_section_id = asset.section_id

                    asset.status = AssetStatus.IN_STORE
                    asset.office_id = stock_return.office_id
                    asset.section_id = stock_return.section_id

                    am = AssetMovement(
                        asset_id=asset.id,
                        movement_type=AssetMovementType.RETURN,
                        from_office_id=from_office_id,
                        from_section_id=from_section_id,
                        to_office_id=stock_return.office_id,
                        to_section_id=stock_return.section_id,
                        reference_document=stock_return.return_no,
                        movement_date=func.now(),
                        remarks=f"Returned via Return #{stock_return.return_no}",
                    )
                    db.add(am)

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
    Atomically post a Stock Transfer document.
    - Check stock availability at from_office
    - Create TRANSFER_OUT movement for source office
    - Create TRANSFER_IN movement for target office
    - Create AssetMovement and update asset location if asset items
    - Lock Transfer document
    """
    transfer = db.query(StockTransfer).filter(StockTransfer.id == transfer_id, StockTransfer.is_active == True).first()
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

    # Validation
    for line in transfer.lines:
        validate_stock_availability(
            db=db,
            item_id=line.item_id,
            office_id=from_stock_office_id,
            required_qty=line.quantity,
            financial_year_id=transfer.financial_year_id,
        )

    try:
        for line in transfer.lines:
            # 1. Stock Movement OUT
            sm_out = StockMovement(
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
            db.add(sm_out)

            # 2. Stock Movement IN
            sm_in = StockMovement(
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
            db.add(sm_in)

            # 3. Asset Transfer
            for line_asset in line.assets:
                asset = line_asset.asset
                if asset:
                    from_office_id = asset.office_id
                    from_section_id = asset.section_id

                    asset.office_id = transfer.to_office_id
                    asset.section_id = transfer.to_section_id

                    am = AssetMovement(
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
                    db.add(am)

        transfer.status = TransactionStatus.POSTED
        transfer.posted_by_id = user_id
        transfer.posted_at = func.now()

        db.commit()
        db.refresh(transfer)
        return transfer
    except Exception:
        db.rollback()
        raise
