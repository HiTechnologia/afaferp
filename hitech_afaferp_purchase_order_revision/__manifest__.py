{
    "name": "HiTech AFAFERP Purchase order revisions",
    "summary": "Keep track of revised quotations",
    "version": "18.0.1.0",
    "category": "Purchase",
    "author": "HiTechnologia",
    "company":"HiTechnologia",
    "license": "AGPL-3",
    "depends": ["hitech_afaferp_purchase_base_revision", "purchase", "base_revision"],
    "data": ["view/purchase_order.xml"],
    "installable": True,
    "post_init_hook": "populate_unrevisioned_name",
}
