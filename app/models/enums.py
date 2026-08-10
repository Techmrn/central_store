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