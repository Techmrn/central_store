from enum import Enum

class Category_Type(str, Enum):
    MATERIAL = "Material"
    ASSET = "Asset"


class AssetStatus(str, Enum):
    IN_STORE = "IN_STORE"
    ISSUED = "ISSUED"
    UNDER_REPAIR = "UNDER_REPAIR"
    DAMAGED = "DAMAGED"
    CONDEMNED = "CONDEMNED"
    E_WASTE = "E_WASTE"
    DISPOSED = "DISPOSED"


class AssetMovementType(str, Enum):
    RECEIPT = "RECEIPT"
    ISSUE = "ISSUE"
    TRANSFER = "TRANSFER"
    RETURN = "RETURN"
    UNSERVICEABLE = "UNSERVICEABLE"
    REPAIR = "REPAIR"
    CONDEMNATION = "CONDEMNATION"
    DISPOSAL = "DISPOSAL"


class UnserviceableStatus(str, Enum):
    UNSERVICEABLE = "UNSERVICEABLE"
    UNDER_REPAIR = "UNDER_REPAIR"
    REPAIRED = "REPAIRED"
    CONDEMNED = "CONDEMNED"
    DISPOSED = "DISPOSED"



class FulfillmentType(str, Enum):
    """How an Indent line is fulfilled.

    STOCK: fulfilled from the stock-owning store.
    PETTY_PURCHASE: planned for direct/local purchase and immediate issue.
    """

    STOCK = "STOCK"
    PETTY_PURCHASE = "PETTY_PURCHASE"


class IndentStatus(str, Enum):
    DRAFT = "DRAFT"
    PROCESSING = "PROCESSING"
    CLOSED = "CLOSED"
    SUBMITTED = "SUBMITTED"
    OFFICE_APPROVED = "OFFICE_APPROVED"
    HEAD_OFFICE_APPROVED = "HEAD_OFFICE_APPROVED"
    SENT_TO_STORE = "SENT_TO_STORE"
    REJECTED = "REJECTED"


class RequestSource(str, Enum):
    PHYSICAL = "PHYSICAL"
    ONLINE = "ONLINE"


class TransactionStatus(str, Enum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    CANCELLED = "CANCELLED"


class MovementType(str, Enum):
    OPENING = "OPENING"
    RECEIPT = "RECEIPT"
    ISSUE = "ISSUE"
    RETURN = "RETURN"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    ADJUSTMENT_IN = "ADJUSTMENT_IN"
    ADJUSTMENT_OUT = "ADJUSTMENT_OUT"


class TransactionSource(str, Enum):
    OPENING = "OPENING"
    HISTORICAL = "HISTORICAL"
    OPERATIONAL = "OPERATIONAL"


class DestinationType(str, Enum):
    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"


