import math

from app.core.constants import PAGE_SIZE


def get_pagination_result(
    query,
    page: int,
):
    total_records = query.count()

    items = (
        query
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )

    return {
        "items": items,
        "current_page": page,
        "page_size": PAGE_SIZE,
        "total_records": total_records,
        "total_pages": (
            math.ceil(total_records / PAGE_SIZE)
            if total_records
            else 1
        ),
    }