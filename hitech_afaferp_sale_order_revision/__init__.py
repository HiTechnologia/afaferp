from . import models


def populate_unrevisioned_name(env):
    env.cr.execute(
        "UPDATE sale_order "
        "SET unrevisioned_name = name "
        "WHERE unrevisioned_name is NULL"
    )
