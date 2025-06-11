from . import models


def populate_unrevisioned_name(cr, registry):
    cr.execute(
        "UPDATE purchase_order "
        "SET unrevisioned_name = name "
        "WHERE unrevisioned_name is NULL"
    )
